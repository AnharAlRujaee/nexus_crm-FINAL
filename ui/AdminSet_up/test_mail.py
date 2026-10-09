"""Card 12 check: send one test e-mail.

    python test_mail.py someone@example.com
"""

import sys

from mailer import MailError, send_emails

if len(sys.argv) < 2:
    raise SystemExit("Usage: python test_mail.py recipient@example.com")

try:
    sent, failures = send_emails([sys.argv[1]], "CRM test email", "Hello from the CRM admin page.")
except MailError as exc:
    raise SystemExit(f"FAILED: {exc}")

print(f"Sent: {sent}")
for address, reason in failures:
    print(f"Failed: {address} ({reason})")
