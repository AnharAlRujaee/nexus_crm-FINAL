"""Send e-mail to event participants over SMTP (Gmail by default).

Configuration comes from environment variables or a ``.env`` file placed next
to this module (KEY=VALUE per line). Nothing secret lives in the code.

    CRM_SMTP_USER       e.g. yourname@gmail.com
    CRM_SMTP_PASSWORD   a Gmail *App Password* (not your normal password)
    CRM_SMTP_HOST       default smtp.gmail.com
    CRM_SMTP_PORT       default 587 (STARTTLS)
    CRM_MAIL_FROM       default: same as CRM_SMTP_USER
"""

import logging
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

import certifi

log = logging.getLogger(__name__)

_ADDRESS_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


class MailError(Exception):
    """Raised with a short, user-presentable message."""


def _load_dotenv() -> None:
    path = Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
    except OSError:
        log.warning("Could not read %s", path)


def _config():
    _load_dotenv()
    user = os.environ.get("CRM_SMTP_USER", "").strip()
    # Google displays App Passwords in four-character groups. Accept that
    # copied format as well as the unspaced value expected by SMTP.
    password = "".join(os.environ.get("CRM_SMTP_PASSWORD", "").split())
    if not user or not password:
        raise MailError("Email not set up - add CRM_SMTP_USER and CRM_SMTP_PASSWORD")
    try:
        port = int(os.environ.get("CRM_SMTP_PORT", "587"))
    except ValueError as exc:
        raise MailError("CRM_SMTP_PORT must be a number") from exc
    return {
        "user": user,
        "password": password,
        "host": os.environ.get("CRM_SMTP_HOST", "smtp.gmail.com").strip(),
        "port": port,
        "sender": os.environ.get("CRM_MAIL_FROM", "").strip() or user,
    }


def is_valid_address(address: str) -> bool:
    return bool(_ADDRESS_RE.match((address or "").strip()))


def send_emails(recipients, subject: str, body: str):
    """Send one separate message to each recipient.

    Returns ``(sent_count, failures)`` where failures is a list of
    ``(address, reason)``. Raises MailError when nothing can be sent at all
    (bad configuration, login rejected, server unreachable).
    """
    recipients = [r.strip() for r in recipients if r and r.strip()]
    if not recipients:
        raise MailError("No recipient address")
    if not (subject or "").strip():
        raise MailError("Subject is empty")

    cfg = _config()
    sent, failures = 0, []
    context = ssl.create_default_context(cafile=certifi.where())

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
            server.starttls(context=context)
            try:
                server.login(cfg["user"], cfg["password"])
            except smtplib.SMTPServerDisconnected as exc:
                raise MailError(
                    "Gmail closed the connection during sign-in. Check the Gmail address "
                    "and App Password, and make sure 2-Step Verification is enabled."
                ) from exc
            for address in recipients:
                if not is_valid_address(address):
                    failures.append((address, "invalid address"))
                    continue
                msg = EmailMessage()
                msg["From"] = cfg["sender"]
                msg["To"] = address
                msg["Subject"] = subject.strip()
                msg.set_content(body)
                try:
                    refused = server.send_message(msg)
                    # smtplib returns a refusal mapping when the server rejects
                    # every recipient; it does not necessarily raise
                    # SMTPRecipientsRefused. Treating that return as success
                    # made the UI report mail as sent when it was not.
                    if address in refused:
                        code, detail = refused[address]
                        reason = detail.decode("utf-8", errors="replace") if isinstance(detail, bytes) else str(detail)
                        failures.append((address, f"SMTP {code}: {reason}"))
                    else:
                        sent += 1
                except smtplib.SMTPRecipientsRefused:
                    failures.append((address, "address refused"))
                except smtplib.SMTPException as exc:
                    failures.append((address, type(exc).__name__))
    except MailError:
        # Preserve the specific error raised while logging in; catching it in
        # the generic handler below would hide the actionable SMTP diagnosis.
        raise
    except smtplib.SMTPAuthenticationError as exc:
        raise MailError("Email login rejected - use a Gmail App Password") from exc
    except ssl.SSLCertVerificationError as exc:
        raise MailError("SSL certificate check failed on this computer") from exc
    except smtplib.SMTPException as exc:
        raise MailError(f"Mail server error: {type(exc).__name__}") from exc
    except OSError as exc:  # DNS, refused, timeout
        raise MailError("Cannot reach mail server - check your connection") from exc
    except Exception as exc:
        log.exception("Unexpected mail error")
        raise MailError("Unexpected email error - see console") from exc

    return sent, failures
