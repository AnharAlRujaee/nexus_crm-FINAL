#!/bin/bash
# One-step setup for the Admin page (Google Calendar + email).
# Put this file in CRM_FINAL/ui/AdminSet_up/ and run:  bash run_setup.sh

cd "$(dirname "$0")" || exit 1
HERE="$(pwd)"
PROJECT_ROOT="$(cd ../.. && pwd)"

echo "== 1/5  Activating your virtual environment"
VENV=""
for candidate in "$PROJECT_ROOT/../.venv" "$HOME/Documents/Python/.venv" "$PROJECT_ROOT/.venv"; do
  if [ -f "$candidate/bin/activate" ]; then VENV="$candidate"; break; fi
done
if [ -z "$VENV" ]; then
  echo "Could not find your .venv. Stopping."; exit 1
fi
source "$VENV/bin/activate"
echo "Using $VENV"

echo
echo "== 2/5  Installing Google libraries"
pip install --quiet google-api-python-client google-auth-httplib2 google-auth-oauthlib || { echo "pip install failed"; exit 1; }

echo
echo "== 3/5  Keeping secrets out of git"
GI="$PROJECT_ROOT/.gitignore"
touch "$GI"
for line in credentials.json 'client_secret*.json' token.json .env; do
  grep -qxF "$line" "$GI" || echo "$line" >> "$GI"
done
echo "Updated $GI"

echo
echo "== 4/5  Email login (.env)"
if [ -f .env ]; then
  echo ".env already exists, keeping it."
else
  cp .env.example .env
  read -r -p "Your Gmail address: " MAIL_USER
  echo "Paste your 16-letter Gmail App Password (typing is hidden)."
  echo "Get one at https://myaccount.google.com/apppasswords"
  read -r -s -p "App Password: " MAIL_PASS
  echo
  MAIL_PASS="${MAIL_PASS// /}"
  printf 'CRM_SMTP_USER=%s\nCRM_SMTP_PASSWORD=%s\n' "$MAIL_USER" "$MAIL_PASS" > .env
  chmod 600 .env
  echo "Created .env"
fi

echo
echo "== 5/5  Optional service tests"
if [ -f credentials.json ] || compgen -G 'client_secret*.json' > /dev/null; then
  echo "-- Calendar (a browser window opens the first time; sign in and allow access)"
  python test_calendar.py
else
  echo "Skipping Calendar test: add your own OAuth credentials.json to enable Calendar."
fi

echo
read -r -p "Send a test email to which address? (Enter to skip): " TEST_TO
if [ -n "$TEST_TO" ]; then
  python test_mail.py "$TEST_TO"
fi

echo
echo "Done. Restart the app and open the Admin Menu."
