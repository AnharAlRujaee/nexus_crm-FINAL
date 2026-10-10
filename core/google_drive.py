"""Google Drive sync for Excel workbooks in the shared CRM folder."""

import io
import os
import re
import sys
import threading
from pathlib import Path

DEFAULT_FOLDER_ID = "1Z3sSNKIbw4WxjESPou584I3MNWYjMSc1"
SOURCE_CONFIG_DIR = Path(__file__).resolve().parent.parent / "ui" / "AdminSet_up"
if getattr(sys, "frozen", False):
    if sys.platform == "win32":
        USER_CONFIG_ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        USER_CONFIG_ROOT = Path.home() / "Library" / "Application Support"
    else:
        USER_CONFIG_ROOT = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    BASE_DIR = USER_CONFIG_ROOT / "NexusCRM"
else:
    BASE_DIR = SOURCE_CONFIG_DIR
CREDENTIALS_FILE = Path(os.environ.get("CRM_GOOGLE_CREDENTIALS", BASE_DIR / "credentials.json"))
TOKEN_FILE = Path(os.environ.get("CRM_GOOGLE_TOKEN", BASE_DIR / "token.json"))
CLIENT_SECRET_PATTERN = re.compile(r"client_secret.*\.json")
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar.events",
]
POLL_INTERVAL_SECONDS = 60

_lock = threading.RLock()
_workbooks = {}
_workbook_versions = {}
_pending_calendar_sync = False


class GoogleAccessError(Exception):
    """A Google OAuth or API problem suitable for translation by the caller."""


class DriveSyncError(Exception):
    """A Google Drive workbook sync problem suitable for display in the UI."""


def _load_local_config():
    try:
        for line in (BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))
    except OSError:
        pass


def get_google_credentials():
    try:
        from google.auth.exceptions import RefreshError, TransportError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise GoogleAccessError(
            f"Google library import failed ({exc.name or exc}) - install the packages in requirements.txt"
        ) from exc

    _load_local_config()
    credentials = None
    if TOKEN_FILE.exists():
        try:
            credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except (ValueError, OSError):
            credentials = None

    if credentials and not credentials.has_scopes(SCOPES):
        credentials = None
    if credentials and not credentials.valid and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError:
            credentials = None
        except TransportError as exc:
            raise GoogleAccessError("Cannot reach Google - check your internet connection") from exc

    if not credentials or not credentials.valid:
        credentials_file = CREDENTIALS_FILE
        if not credentials_file.exists():
            try:
                candidates = sorted(
                    path for path in BASE_DIR.iterdir()
                    if path.is_file() and CLIENT_SECRET_PATTERN.fullmatch(path.name)
                )
            except OSError:
                candidates = []
            credentials_file = candidates[0] if candidates else None
        if credentials_file is None or not credentials_file.exists():
            raise GoogleAccessError(f"credentials.json not found at {CREDENTIALS_FILE}")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            login_hint = os.environ.get("CRM_GOOGLE_USER", "nexuscrmt@gmail.com").strip()
            options = {"login_hint": login_hint} if login_hint else {}
            credentials = flow.run_local_server(port=0, timeout_seconds=180, **options)
        except Exception as exc:
            raise GoogleAccessError("Google sign-in failed or was cancelled") from exc
        try:
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
            os.chmod(TOKEN_FILE, 0o600)
        except OSError:
            pass
    return credentials


def _drive_service():
    try:
        from googleapiclient.discovery import build

        return build("drive", "v3", credentials=get_google_credentials(), cache_discovery=False)
    except GoogleAccessError as exc:
        raise DriveSyncError(str(exc)) from exc
    except ImportError as exc:
        raise DriveSyncError("Google Drive libraries are missing - install requirements.txt") from exc
    except Exception as exc:
        raise DriveSyncError("Could not start the Google Drive service") from exc


def _folder_id():
    _load_local_config()
    return os.environ.get("CRM_GOOGLE_DRIVE_FOLDER_ID", DEFAULT_FOLDER_ID)


def _list_children(service, folder_id):
    page_token = None
    try:
        while True:
            response = service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken,files(id,name,mimeType,md5Checksum,modifiedTime)",
                pageSize=1000,
                pageToken=page_token,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()
            yield from response.get("files", [])
            page_token = response.get("nextPageToken")
            if not page_token:
                break
    except Exception as exc:
        raise DriveSyncError("Could not list the shared Drive folder - check access and connection") from exc


def _list_workbooks(service):
    found = []
    pending = [_folder_id()]
    while pending:
        for item in _list_children(service, pending.pop()):
            if item.get("mimeType") == "application/vnd.google-apps.folder":
                pending.append(item["id"])
            elif item.get("name", "").casefold().endswith((".xlsx", ".xlsm")):
                found.append(item)
    return found


def sync_workbooks(force=False):
    """Sync all Excel files recursively; only download files whose version changed."""
    global _workbooks, _workbook_versions, _pending_calendar_sync
    with _lock:
        service = _drive_service()
        remote = _list_workbooks(service)
        items = {}
        for item in remote:
            key = item["name"].casefold()
            if key in items:
                raise DriveSyncError(f"More than one {item['name']} exists in the shared Drive folder")
            items[key] = item

        changed = set(items) != set(_workbooks)
        next_workbooks, next_versions = {}, {}
        for key, item in items.items():
            version = item.get("md5Checksum") or item.get("modifiedTime") or item["id"]
            if not force and _workbook_versions.get(key) == version and key in _workbooks:
                content = _workbooks[key]
            else:
                try:
                    content = service.files().get_media(
                        fileId=item["id"], supportsAllDrives=True
                    ).execute()
                except Exception as exc:
                    raise DriveSyncError(f"Could not download {item['name']} from Google Drive") from exc
                changed = changed or _workbook_versions.get(key) != version
            next_workbooks[key] = content
            next_versions[key] = version
        _workbooks, _workbook_versions = next_workbooks, next_versions
        _pending_calendar_sync = _pending_calendar_sync or changed
        return changed


def consume_calendar_sync_request():
    """Return and clear whether any caller observed changed Drive workbooks."""
    global _pending_calendar_sync
    with _lock:
        pending = _pending_calendar_sync
        _pending_calendar_sync = False
        return pending


def download_workbook(filename):
    """Return the latest workbook bytes, syncing changed files first."""
    sync_workbooks()
    try:
        return _workbooks[filename.casefold()]
    except KeyError as exc:
        raise DriveSyncError(f"{filename} was not found in the shared Google Drive folder") from exc


def upload_workbook(filename, content):
    """Replace a workbook in Drive, used when signing up a new user."""
    try:
        from googleapiclient.http import MediaIoBaseUpload
    except ImportError as exc:
        raise DriveSyncError("Google Drive libraries are missing - install requirements.txt") from exc

    with _lock:
        service = _drive_service()
        matches = [item for item in _list_workbooks(service)
                   if item["name"].casefold() == filename.casefold()]
        if len(matches) != 1:
            raise DriveSyncError(f"Could not identify a unique {filename} in the shared Drive folder")
        upload = MediaIoBaseUpload(
            io.BytesIO(content),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        try:
            service.files().update(
                fileId=matches[0]["id"], media_body=upload, supportsAllDrives=True, fields="id"
            ).execute()
        except Exception as exc:
            raise DriveSyncError(
                f"Could not update {filename} in Google Drive - check that you have edit access"
            ) from exc
        _workbooks.pop(filename.casefold(), None)
        _workbook_versions.pop(filename.casefold(), None)


def get_cached_workbook(filename):
    with _lock:
        return _workbooks.get(filename.casefold())


def cached_workbook_names():
    with _lock:
        return tuple(sorted(_workbooks))