"""Load CRM records from the Excel files in ./data (Drive export)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import pandas as pd


def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def data_dir() -> str:
    return os.path.join(app_dir(), "data")


def data_file(name: str) -> str:
    return os.path.join(data_dir(), name)


def _cell(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "nat", "none", "<na>"}:
        return ""
    if text.endswith(".0") and text.replace(".", "", 1)[:-1].isdigit():
        return text[:-2]
    return text


def _norm_name(value: str) -> str:
    return " ".join(_cell(value).lower().split())


def name_matches(full_name: str, query: str) -> bool:
    """Match first name or surname prefixes, e.g. 'As' → 'asiye turan'."""
    q = query.strip().lower()
    if not q:
        return True
    name = _cell(full_name).lower()
    if name.startswith(q):
        return True
    return any(part.startswith(q) for part in name.replace("-", " ").split())


@dataclass
class SheetTable:
    headers: list[str]
    rows: list[list[str]]

    def name_index(self) -> int:
        for key in ("Full Name", "Candidate Name", "Name"):
            if key in self.headers:
                return self.headers.index(key)
        return 0

    def col(self, *names: str) -> int | None:
        lookup = {h.lower(): i for i, h in enumerate(self.headers)}
        for name in names:
            i = lookup.get(name.lower())
            if i is not None:
                return i
        return None

    def names(self) -> set[str]:
        i = self.name_index()
        return {_norm_name(row[i]) for row in self.rows if _cell(row[i])}

    def filtered_by_name(self, query: str) -> list[list[str]]:
        i = self.name_index()
        return [row for row in self.rows if name_matches(row[i], query)]


def load_sheet(filename: str, sheet: int | str = 0) -> SheetTable:
    path = data_file(filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{filename} not found in {data_dir()}")
    df = pd.read_excel(path, sheet_name=sheet, dtype=str)
    df.columns = [_cell(c) for c in df.columns]
    df = df.map(_cell)
    headers = list(df.columns)
    rows = df.values.tolist()
    return SheetTable(headers=headers, rows=rows)


def load_applications() -> SheetTable:
    return load_sheet("Applications.xlsx")


def load_mentor() -> SheetTable:
    return load_sheet("Mentor.xlsx", sheet="Mentor")


def load_mentor_recommendations() -> list[str]:
    table = load_sheet("Mentor.xlsx", sheet="Mentor Recommendation Options")
    values = []
    for row in table.rows:
        text = _cell(row[0]) if row else ""
        if text:
            values.append(text)
    return values


def load_interviews() -> SheetTable:
    return load_sheet("Interviews.xlsx")


def is_blank(value: str) -> bool:
    return not _cell(value)


def meeting_identified(value: str) -> bool:
    text = _cell(value).lower()
    if not text:
        return False
    if text in {"not assigned", "no", "none", "n/a", "-"}:
        return False
    return True


def application_duplicates(table: SheetTable) -> list[list[str]]:
    name_i = table.col("Full Name") or 0
    email_i = table.col("Email") or 1
    counts: dict[tuple[str, str], int] = {}
    for row in table.rows:
        key = (_norm_name(row[name_i]), _cell(row[email_i]).lower())
        counts[key] = counts.get(key, 0) + 1
    return [
        row for row in table.rows
        if counts[(_norm_name(row[name_i]), _cell(row[email_i]).lower())] > 1
    ]


def unique_applications(table: SheetTable) -> list[list[str]]:
    name_i = table.col("Full Name") or 0
    seen: set[str] = set()
    out = []
    for row in table.rows:
        key = _norm_name(row[name_i])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def previous_vit_rows(apps: SheetTable, mentor: SheetTable, interviews: SheetTable) -> list[list[str]]:
    """Candidates who appear in Applications and at least one other VIT file."""
    other = mentor.names() | interviews.names()
    i = apps.name_index()
    return [row for row in apps.rows if _norm_name(row[i]) in other]


def different_record_rows(mentor: SheetTable, interviews: SheetTable) -> tuple[list[str], list[list[str]]]:
    """People in Mentor or Interviews, but not in both."""
    m_names = mentor.names()
    i_names = interviews.names()
    only_m = sorted(m_names - i_names)
    only_i = sorted(i_names - m_names)
    headers = ["Full Name", "Found in Mentor", "Found in Interviews"]
    rows = []
    for name in only_m:
        rows.append([name.title(), "Yes", "No"])
    for name in only_i:
        rows.append([name.title(), "No", "Yes"])
    return headers, rows
