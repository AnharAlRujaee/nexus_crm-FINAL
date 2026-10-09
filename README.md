# NEXUS CRM — Futuristic PyQt6 Interface

CRM capstone: every window is built, styled, animated and navigable. Workbook
data syncs from the shared Google Drive folder. Dated Applications, Mentor and
Interviews rows are mirrored into Google Calendar; the Admin page loads events
from that calendar and can send email to selected participants.

## Run

```bash
pip install -r requirements.txt     # PyQt6, openpyxl, and Google API libraries
python main.py
```

## Project layout

```
main.py                          window controller + navigation logic
core/
  data_store.py                  reads the shared workbooks and maps dated rows
  google_drive.py                Google Drive sync and OAuth credentials
  filters.py                     search / duplicate / category matching
ui/
  data_table.py                  sortable, scrollable data table + record dialog
  theme.py                       colours, fonts, global stylesheet
  icons.py                       vector icons drawn in code (no image files)
  background.py                  animated aurora / grid / particle background
  widgets.py                     glow buttons, glass panels, nav cards, toasts...
  navigation.py                  animated page transitions (slide + fade + light beam)
  base_page.py                   shared page skeleton + staggered reveal
  AdminSet_up/                    Google Calendar and SMTP integration
pages/
  login_page.py                  1. Login
  signup_page.py                 Sign Up (opened from the Login card)
  preferences_page.py            2. Preferences (regular user)
  preferences_admin_page.py      3. Preferences (admin)
  applications_page.py           4. Applications
  mentor_page.py                 5. Mentor Interview
  interviews_page.py             6. Interviews
  admin_page.py                  7. Admin Menu
```

## Navigation

Login → Preferences → Applications / Mentor Interview / Interviews → back.
Admins also get Preferences (Admin) → Admin Menu → back.
Every "Return to Preferences Screen" button sends admins to the Admin
preferences and everyone else to the regular preferences.

### Data (Google Drive)

| File | Used by |
|------|---------|
| `Users.xlsx` (Username, Password, Role) | Login / Sign up. Role `admin` opens the Admin preferences. |
| `Applications.xlsx` | Applications - all 27 columns, search, mentor-meeting filters, duplicate views |
| `Mentor.xlsx` (+ *Mentor Recommendation Options* sheet) | Mentor Interview - search + category dropdown |
| `Interviews.xlsx` | Interviews - search + Projects Sent / Received |

All `.xlsx` and `.xlsm` files in the shared Drive folder and subfolders are
synced. Data pages check for updates when opened; after login, the app polls
every 60 seconds and refreshes the visible data page. Changes are also mirrored
to Google Calendar. Sign Up updates the shared `Users.xlsx`. OAuth setup is in
[`ui/AdminSet_up/SETUP.md`](ui/AdminSet_up/SETUP.md).

### Tables

Click a header to sort, drag column edges to resize, scroll sideways for wide
sheets, hover long text for the full value, double-click a row for every field.
Search matches the start of a name or surname ("as" finds *Asiye Turan*).

### Login

Use an account from the shared `Users.xlsx`. The eye icon in the password field
shows or hides what you type. Sign up adds a regular `user` account to it.

### Admin Calendar and Email

Applications submission timestamps, Mentor dates and Interviews project sent /
received dates create managed Calendar events. Events are updated when workbook
rows change and removed if their source row is removed. The Admin page loads the
configured Calendar, allows filtering by event, participant, email or status,
then opens Mail for the selected attendees. Setup requires Drive and Calendar
OAuth permissions plus SMTP credentials; see
[`ui/AdminSet_up/SETUP.md`](ui/AdminSet_up/SETUP.md). OAuth credentials, tokens,
and SMTP `.env` settings are local-only and excluded from Git.

## Design notes

- Live background: drifting aurora, scrolling perspective grid, particle
  constellation that follows the mouse, and a colour that morphs to each page's accent.
- One accent colour per section (violet login, cyan preferences, pink admin,
  blue applications, amber mentor, green interviews).
- Page transitions: parallax slide + cross-fade + a neon light beam,
  then the page's panels/cards reveal one after another.
- Custom-painted controls with hover halo, shine sweep, pressed state and rounded edges.
- Everything is vector-drawn, so it is crisp at any display scale.

## Not implemented yet (later stages)

The VIT1 / VIT2 comparison filters need the corresponding VIT workbooks in the
shared Drive folder.
