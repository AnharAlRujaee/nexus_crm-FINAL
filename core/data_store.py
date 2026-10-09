"""Excel data layer: reads (and, for sign-up, writes) the workbooks in ``data/``.

Pure Python - no Qt imports - so it can be tested on its own.

    Applications.xlsx   ->  load_applications()
    Mentor.xlsx         ->  load_mentor(), load_mentor_options()
    Interviews.xlsx     ->  load_interviews()
    Users.xlsx          ->  authenticate(), register_user()

Every loader returns a ``Table`` with the headers and rows in exactly the
order they appear in the spreadsheet. Empty cells are ``None``.
"""

import os
import sys
from datetime import date, datetime

from openpyxl import load_workbook


class DataError(Exception):
    """A problem with a data file, worded so it can be shown to the user."""


def app_dir() -> str:
    """Folder that holds ``data/`` - next to the .exe when frozen, else the project root."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DATA_DIR = os.path.join(app_dir(), "data")


class Table:
    """Headers plus rows, in spreadsheet order."""

    def __init__(self, headers, rows):
        self.headers = list(headers)
        self.rows = [list(r) for r in rows]

    def index(self, name: str) -> int:
        """Column position of ``name`` (case-insensitive), or -1 when absent."""
        wanted = name.strip().casefold()
        for i, header in enumerate(self.headers):
            if header.strip().casefold() == wanted:
                return i
        return -1


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def _clean(value):
    """Normalise one cell: trim text, turn 22.0 into 22, dates into text, '' into None."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M") if (value.hour or value.minute) else value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def read_table(filename: str, sheet: str = None) -> Table:
    """Read one worksheet. The first non-empty row is the header row."""
    path = _path(filename)
    if not os.path.isfile(path):
        raise DataError(f"{filename} was not found in the data folder.")
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # corrupt file, permission problem, ...
        raise DataError(f"{filename} could not be opened ({exc.__class__.__name__}).") from exc

    try:
        if sheet is None:
            worksheet = workbook.worksheets[0]
        elif sheet in workbook.sheetnames:
            worksheet = workbook[sheet]
        else:
            raise DataError(f"{filename} has no sheet called '{sheet}'.")

        headers, rows = None, []
        for raw in worksheet.iter_rows(values_only=True):
            cells = [_clean(c) for c in raw]
            if headers is None:
                if any(c is not None for c in cells):
                    names = ["" if c is None else str(c) for c in cells]
                    while names and not names[-1]:      # drop trailing blank header cells
                        names.pop()
                    headers = names
                continue
            if all(c is None for c in cells):
                continue
            cells = (cells + [None] * len(headers))[: len(headers)]
            rows.append(cells)
    finally:
        workbook.close()

    if headers is None:
        raise DataError(f"{filename} is empty.")
    return Table(headers, rows)


def load_applications() -> Table:
    return read_table("Applications.xlsx")


def load_mentor() -> Table:
    return read_table("Mentor.xlsx", "Mentor")


def load_mentor_options() -> list:
    """The recommendation options from the 'Mentor Recommendation Options' sheet."""
    table = read_table("Mentor.xlsx", "Mentor Recommendation Options")
    return [str(r[0]) for r in table.rows if r and r[0]]


def load_interviews() -> Table:
    return read_table("Interviews.xlsx")


# ---------------------------------------------------------------------------
# Users: login + sign-up
# ---------------------------------------------------------------------------
def authenticate(username: str, password: str):
    """Check a login against Users.xlsx.

    Returns ``(username_as_stored, role)`` with role ``"admin"`` or ``"user"``,
    or ``None`` when the credentials do not match. Usernames are not
    case-sensitive; passwords are.
    """
    table = read_table("Users.xlsx")
    iu, ip, ir = table.index("Username"), table.index("Password"), table.index("Role")
    if iu < 0 or ip < 0:
        raise DataError("Users.xlsx needs 'Username' and 'Password' columns.")

    wanted = username.strip().casefold()
    for row in table.rows:
        stored_user = "" if row[iu] is None else str(row[iu])
        stored_pass = "" if row[ip] is None else str(row[ip])
        if stored_user.casefold() == wanted and stored_pass == password:
            role = str(row[ir]).strip().lower() if ir >= 0 and row[ir] is not None else "user"
            return stored_user, ("admin" if role == "admin" else "user")
    return None


def register_user(username: str, password: str, role: str = "user") -> None:
    """Append a new account to Users.xlsx. Raises DataError if it cannot be saved."""
    path = _path("Users.xlsx")
    if not os.path.isfile(path):
        raise DataError("Users.xlsx was not found in the data folder.")
    try:
        workbook = load_workbook(path)
    except Exception as exc:
        raise DataError(f"Users.xlsx could not be opened ({exc.__class__.__name__}).") from exc

    sheet = workbook.worksheets[0]
    header_row = [("" if c.value is None else str(c.value).strip().casefold()) for c in sheet[1]]
    try:
        col_user = header_row.index("username")
        col_pass = header_row.index("password")
    except ValueError:
        raise DataError("Users.xlsx needs 'Username' and 'Password' columns.") from None
    col_role = header_row.index("role") if "role" in header_row else None

    taken = {
        str(r[col_user]).strip().casefold()
        for r in sheet.iter_rows(min_row=2, values_only=True)
        if len(r) > col_user and r[col_user] is not None
    }
    if username.strip().casefold() in taken:
        raise DataError("That username is already taken.")

    new_row = [None] * len(header_row)
    new_row[col_user] = username.strip()
    new_row[col_pass] = password
    if col_role is not None:
        new_row[col_role] = role
    sheet.append(new_row)

    temp = path + ".tmp"
    try:
        workbook.save(temp)
        os.replace(temp, path)
    except OSError as exc:
        try:
            os.remove(temp)
        except OSError:
            pass
        raise DataError("Could not save Users.xlsx - close it in Excel and try again.") from exc
