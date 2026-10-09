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
import hashlib
import os
import re
from datetime import datetime, timedelta, timezone

from core.google_drive import GoogleAccessError, get_google_credentials
from core.data_store import DataError, load_calendar_source_events

log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


class CalendarError(Exception):
    """Raised with a short, user-presentable message."""


def _calendar_id():
    return os.environ.get("CRM_GOOGLE_CALENDAR_ID", "primary").strip() or "primary"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def _build_service():
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise CalendarError(
            "Google libraries missing - install google-api-python-client, "
            "google-auth-httplib2 and google-auth-oauthlib"
        ) from exc

    try:
        creds = get_google_credentials()
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except GoogleAccessError as exc:
        log.warning("Google sign-in failed: %s", exc)
        raise CalendarError(f"{exc} - press Event Record to try again") from exc
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
def fetch_events(max_results: int = 2500, calendar_id: str | None = None, days_back: int = 3650):
    """Return events from ``days_back`` days ago onwards, oldest first."""
    try:
        from googleapiclient.errors import HttpError
    except ImportError as exc:
        raise CalendarError("Google libraries missing - see setup notes") from exc

    service = _build_service()
    calendar_id = calendar_id or _calendar_id()
    time_min = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

    events = []
    page_token = None
    try:
        while len(events) < max_results:
            response = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                maxResults=min(max_results - len(events), 2500),
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            ).execute()
            for raw in response.get("items", []):
                try:
                    events.append(parse_event(raw))
                except (ValueError, KeyError, TypeError):
                    log.warning("Skipping unreadable event %s", raw.get("id"))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
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
    except CalendarError:
        raise
    except Exception as exc:  # anything unexpected must not crash the app
        log.exception("Unexpected calendar error")
        raise CalendarError("Unexpected calendar error - see console") from exc
    return events


def sync_events_from_workbooks():
    """Create or update CRM-managed events based on dated rows in its workbooks."""
    try:
        from googleapiclient.errors import HttpError
    except ImportError as exc:
        raise CalendarError("Google libraries missing - install requirements.txt") from exc

    try:
        source_events = load_calendar_source_events()
    except DataError as exc:
        raise CalendarError(str(exc)) from exc
    service = _build_service()
    calendar_id = _calendar_id()
    desired_keys = set()

    for source in source_events:
        source_key = source["source_key"]
        desired_keys.add(source_key)
        event_id = "crm" + hashlib.sha256(source_key.encode("utf-8")).hexdigest()
        body = {
            "id": event_id,
            "summary": source["title"],
            "description": source["description"],
            "start": source["start"],
            "end": source["end"],
            "status": "confirmed",
            "extendedProperties": {
                "private": {"nexusCrmManaged": "true", "nexusCrmSourceKey": source_key}
            },
        }
        try:
            existing = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        except HttpError as exc:
            if getattr(exc.resp, "status", None) != 404:
                raise CalendarError(f"Could not check Calendar event {source['title']}") from exc
            existing = None
        try:
            if existing:
                fields = ("summary", "description", "start", "end", "status", "extendedProperties")
                if any(existing.get(field) != body.get(field) for field in fields):
                    service.events().patch(calendarId=calendar_id, eventId=event_id, body=body).execute()
            else:
                service.events().insert(calendarId=calendar_id, body=body).execute()
        except HttpError as exc:
            if getattr(exc.resp, "status", None) == 409:
                service.events().patch(calendarId=calendar_id, eventId=event_id, body=body).execute()
            else:
                raise CalendarError(f"Could not sync Calendar event {source['title']}") from exc

    _remove_stale_managed_events(service, calendar_id, desired_keys)
    return len(source_events)


def _remove_stale_managed_events(service, calendar_id, desired_keys):
    """Remove only events previously created by CRM whose source row disappeared."""
    page_token = None
    try:
        stale_ids = []
        while True:
            response = service.events().list(
                calendarId=calendar_id,
                privateExtendedProperty="nexusCrmManaged=true",
                maxResults=2500,
                pageToken=page_token,
            ).execute()
            for event in response.get("items", []):
                private = event.get("extendedProperties", {}).get("private", {})
                source_key = private.get("nexusCrmSourceKey")
                if source_key and source_key not in desired_keys:
                    stale_ids.append(event["id"])
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        for event_id in stale_ids:
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except Exception as exc:
        log.exception("Could not reconcile old CRM-managed calendar events")
        raise CalendarError("Could not reconcile old CRM-managed calendar events") from exc
