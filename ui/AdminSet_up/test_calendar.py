"""Card 6 / 10 check: can Python read the Google Calendar?

Run from the folder that contains calendar_service.py:
    python test_calendar.py
The first run opens a browser to sign in and creates token.json.
"""

from calendar_service import CalendarError, fetch_events

try:
    events = fetch_events()
except CalendarError as exc:
    raise SystemExit(f"FAILED: {exc}")

print(f"{len(events)} event(s) found\n")
for e in events:
    print(f"{e['date']}  {e['time']:<8} {e['title']}")
    print(f"    participants: {e['participants']}")
    print(f"    emails:       {', '.join(e['emails']) or '-'}")
    print(f"    status:       {e['status']}\n")
