"""Google Calendar access for the Admin page (read-only).

Public API
----------
fetch_events(...)  -> list of event dicts ready for the table
parse_event(raw)   -> convert one raw Google API event into a flat dict
CalendarError      -> the only exception the UI needs to catch

Files (next to this module, override with environment variables):
    credentials.json   OAuth client downloaded from Google Cloud Console
    token.json         created automatically after the first sign-in
"""

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = Path(os.environ.get("CRM_GOOGLE_CREDENTIALS", BASE_DIR / "credentials.json"))
TOKEN_FILE = Path(os.environ.get("CRM_GOOGLE_TOKEN", BASE_DIR / "token.json"))

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


class CalendarError(Exception):
    """Raised with a short, user-presentable message."""


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
SIGN_IN_TIMEOUT = 180  # seconds to wait for the browser sign-in before giving up


def _find_credentials_file():
    """credentials.json, or the client_secret*.json exactly as Google names it."""
    if CREDENTIALS_FILE.exists():
        return CREDENTIALS_FILE
    for candidate in sorted(BASE_DIR.glob("client_secret*.json")):
        return candidate
    return None


def _build_service():
    try:
        from google.auth.exceptions import RefreshError, TransportError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise CalendarError(
            "Google libraries missing - install google-api-python-client, "
            "google-auth-httplib2 and google-auth-oauthlib"
        ) from exc

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except (ValueError, OSError):
            creds = None  # unreadable token -> sign in again

    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None  # revoked / expired refresh token -> sign in again
        except TransportError as exc:
            raise CalendarError("Cannot reach Google - check your internet connection") from exc

    if not creds or not creds.valid:
        credentials_file = _find_credentials_file()
        if credentials_file is None:
            raise CalendarError(f"credentials.json not found at {CREDENTIALS_FILE}")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            creds = flow.run_local_server(port=0, timeout_seconds=SIGN_IN_TIMEOUT)
        except Exception as exc:  # bad file, closed browser, timeout, denied consent
            log.warning("Google sign-in failed: %s", exc)
            raise CalendarError("Google sign-in failed or was cancelled - press Event Record to try again") from exc
        try:
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        except OSError:
            log.warning("Could not save %s", TOKEN_FILE)

    try:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as exc:
        log.exception("Could not create the Calendar service")
        raise CalendarError("Could not start the Google Calendar service - see console") from exc


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def _split_when(node):
    """Return (date, time) strings for a Google start/end node."""
    if not node:
        return "", ""
    if "dateTime" in node:
        dt = datetime.fromisoformat(node["dateTime"]).astimezone()  # local time
        return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M")
    if "date" in node:  # all-day event
        d = datetime.fromisoformat(node["date"])
        return d.strftime("%d/%m/%Y"), "All day"
    return "", ""


def parse_event(raw: dict) -> dict:
    """Flatten one raw Google Calendar event.

    Emails come from the guest list (excluding the calendar owner and rooms).
    If the event has no guests, any address typed into the title/description
    is used instead, so simple test events still work.
    """
    date, time_ = _split_when(raw.get("start"))

    names, emails = [], []
    for att in raw.get("attendees", []) or []:
        if att.get("self") or att.get("resource"):
            continue
        email = (att.get("email") or "").strip()
        if not email:
            continue
        emails.append(email)
        names.append((att.get("displayName") or email).strip())

    if not emails:
        text = f"{raw.get('summary', '')} {raw.get('description', '')}"
        for match in _EMAIL_RE.findall(text):
            if match not in emails:
                emails.append(match)
                names.append(match)

    return {
        "id": raw.get("id", ""),
        "title": (raw.get("summary") or "(no title)").strip(),
        "date": date,
        "time": time_,
        "participants": ", ".join(names) if names else "\u2014",
        "emails": emails,
        "status": (raw.get("status") or "confirmed").upper(),
    }


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
def fetch_events(max_results: int = 100, calendar_id: str = "primary", days_back: int = 30):
    """Return events from ``days_back`` days ago onwards, oldest first."""
    try:
        from googleapiclient.errors import HttpError
    except ImportError as exc:
        raise CalendarError("Google libraries missing - see setup notes") from exc

    service = _build_service()
    time_min = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

    try:
        response = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
    except HttpError as exc:
        status = getattr(exc.resp, "status", 0)
        if status in (401, 403):
            raise CalendarError("Google denied access - check API is enabled and test user added") from exc
        if status == 404:
            raise CalendarError("Calendar not found") from exc
        if status == 429:
            raise CalendarError("Google rate limit reached - try again shortly") from exc
        raise CalendarError(f"Google Calendar error ({status})") from exc
    except OSError as exc:  # no internet, DNS, timeout
        raise CalendarError("Cannot reach Google - check your internet connection") from exc
    except Exception as exc:  # anything unexpected must not crash the app
        log.exception("Unexpected calendar error")
        raise CalendarError("Unexpected calendar error - see console") from exc

    events = []
    for raw in response.get("items", []):
        try:
            events.append(parse_event(raw))
        except (ValueError, KeyError, TypeError):
            log.warning("Skipping unreadable event %s", raw.get("id"))
    return events
