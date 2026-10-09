"""Workbook data layer backed by the configured shared Google Drive folder.

Pure Python - no Qt imports - so it can be tested on its own.

    Applications.xlsx   ->  load_applications()
    Mentor.xlsx         ->  load_mentor(), load_mentor_options()
    Interviews.xlsx     ->  load_interviews()
    Users.xlsx          ->  authenticate(), register_user()

Every loader returns a ``Table`` with the headers and rows in exactly the
order they appear in the spreadsheet. Empty cells are ``None``.
"""

import io
from datetime import date, datetime, time, timedelta

from openpyxl import load_workbook

from core.google_drive import (
    DriveSyncError, cached_workbook_names, download_workbook,
    get_cached_workbook, sync_workbooks, upload_workbook,
)

class DataError(Exception):
    """A problem with a data file, worded so it can be shown to the user."""


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


def read_table(filename: str, sheet: str | None = None) -> Table:
    """Read the current Drive workbook. The first non-empty row is the header."""
    try:
        content = download_workbook(filename)
    except DriveSyncError as exc:
        raise DataError(str(exc)) from exc
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # corrupt file, permission problem, ...
        raise DataError(f"{filename} from Google Drive could not be opened ({exc.__class__.__name__}).") from exc

    try:
        if sheet is None:
            worksheet = workbook.worksheets[0]
        elif sheet in workbook.sheetnames:
            worksheet = workbook[sheet]
        else:
            raise DataError(f"{filename} has no sheet called '{sheet}'.")
        return _table_from_worksheet(worksheet, filename)
    finally:
        workbook.close()


def _table_from_worksheet(worksheet, source: str) -> Table:
    headers, rows = None, []
    for raw in worksheet.iter_rows(values_only=True):
        cells = [_clean(c) for c in raw]
        if headers is None:
            if any(c is not None for c in cells):
                names = ["" if c is None else str(c) for c in cells]
                while names and not names[-1]:
                    names.pop()
                headers = names
            continue
        if all(c is None for c in cells):
            continue
        cells = (cells + [None] * len(headers))[: len(headers)]
        rows.append(cells)
    if headers is None:
        raise DataError(f"{source} is empty.")
    return Table(headers, rows)


def read_all_tables() -> list:
    """Read every worksheet in every Excel workbook found in the Drive share."""
    try:
        sync_workbooks()
    except DriveSyncError as exc:
        raise DataError(str(exc)) from exc

    tables = []
    for filename in cached_workbook_names():
        content = get_cached_workbook(filename)
        if content is None:
            continue
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as exc:
            raise DataError(f"{filename} from Google Drive could not be opened ({exc.__class__.__name__}).") from exc
        try:
            for worksheet in workbook.worksheets:
                try:
                    tables.append((filename, worksheet.title, _table_from_worksheet(worksheet, filename)))
                except DataError:
                    continue
        finally:
            workbook.close()
    return tables


def _parse_event_date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if value is None:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for pattern in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def load_calendar_source_events():
    """Build managed Calendar events from dated rows in the three CRM workbooks."""
    applications = load_applications()
    mentor = load_mentor()
    interviews = load_interviews()

    email_by_name = {}
    app_name_index, app_email_index = applications.index("Full Name"), applications.index("Email")
    if app_name_index >= 0 and app_email_index >= 0:
        for row in applications.rows:
            if row[app_name_index] and row[app_email_index]:
                email_by_name.setdefault(str(row[app_name_index]).strip().casefold(), str(row[app_email_index]).strip())

    events = []

    def add_event(source, row_number, phase, title, raw_date, participant, email=""):
        parsed = _parse_event_date(raw_date)
        if parsed is None:
            return
        if parsed.hour or parsed.minute or parsed.second:
            local_start = parsed.astimezone()
            start = {"dateTime": local_start.isoformat()}
            end = {"dateTime": (local_start + timedelta(minutes=30)).isoformat()}
        else:
            start_day = parsed.date()
            start = {"date": start_day.isoformat()}
            end = {"date": (start_day + timedelta(days=1)).isoformat()}
        description = f"Automatically synced from NEXUS CRM: {source}."
        if participant:
            description += f"\nParticipant: {participant}."
        if email:
            description += f"\nContact email: {email}."
        events.append({
            "source_key": f"{source}:{row_number}:{phase}",
            "title": title,
            "start": start,
            "end": end,
            "description": description,
            "participant": participant or "",
            "emails": [email] if email else [],
            "status": "CONFIRMED",
        })

    app_date_index = applications.index("Applications Timestamp")
    if app_name_index >= 0 and app_date_index >= 0:
        for row_number, row in enumerate(applications.rows, start=2):
            name = str(row[app_name_index]).strip() if row[app_name_index] else "Applicant"
            email = str(row[app_email_index]).strip() if app_email_index >= 0 and row[app_email_index] else ""
            add_event("Applications", row_number, "received", f"Application received: {name}",
                      row[app_date_index], name, email)

    mentor_date_index = mentor.index("Mentor Date")
    candidate_index, mentor_name_index = mentor.index("Candidate Name"), mentor.index("Mentor Name")
    if mentor_date_index >= 0 and candidate_index >= 0:
        for row_number, row in enumerate(mentor.rows, start=2):
            name = str(row[candidate_index]).strip() if row[candidate_index] else "Candidate"
            mentor_name = str(row[mentor_name_index]).strip() if mentor_name_index >= 0 and row[mentor_name_index] else ""
            title = f"Mentor meeting: {name}" + (f" with {mentor_name}" if mentor_name else "")
            add_event("Mentor", row_number, "meeting", title, row[mentor_date_index], name,
                      email_by_name.get(name.casefold(), ""))

    interview_name_index = interviews.index("Full Name")
    if interview_name_index >= 0:
        for phase, date_header in (("project-sent", "Project Sent Date"),
                                   ("project-received", "Project Received Date")):
            date_index = interviews.index(date_header)
            if date_index < 0:
                continue
            for row_number, row in enumerate(interviews.rows, start=2):
                name = str(row[interview_name_index]).strip() if row[interview_name_index] else "Candidate"
                label = "Project sent" if phase == "project-sent" else "Project received"
                add_event("Interviews", row_number, phase, f"{label}: {name}", row[date_index], name,
                          email_by_name.get(name.casefold(), ""))
    return events


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
    """Check a login against the current Users.xlsx in Google Drive.

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
    """Append a new account to the shared Users.xlsx workbook."""
    try:
        content = download_workbook("Users.xlsx")
        workbook = load_workbook(io.BytesIO(content))
    except DriveSyncError as exc:
        raise DataError(str(exc)) from exc
    except Exception as exc:
        raise DataError(f"Users.xlsx from Google Drive could not be opened ({exc.__class__.__name__}).") from exc

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

    new_row: list[object] = [None] * len(header_row)
    new_row[col_user] = username.strip()
    new_row[col_pass] = password
    if col_role is not None:
        new_row[col_role] = role
    sheet.append(new_row)

    try:
        output = io.BytesIO()
        workbook.save(output)
        upload_workbook("Users.xlsx", output.getvalue())
    except DriveSyncError as exc:
        raise DataError(str(exc)) from exc
    except Exception as exc:
        raise DataError(f"Could not update Users.xlsx in Google Drive ({exc.__class__.__name__}).") from exc
    finally:
        workbook.close()
