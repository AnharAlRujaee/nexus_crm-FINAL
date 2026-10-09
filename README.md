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

The CRM data source is the shared [Google Drive data folder](https://drive.google.com/drive/folders/1Z3sSNKIbw4WxjESPou584I3MNWYjMSc1?usp=share_link).
The default folder ID is `1Z3sSNKIbw4WxjESPou584I3MNWYjMSc1`.

| File | Used by |
|------|---------|
| `Users.xlsx` (Username, Password, Role) | Login / Sign up. Role `admin` opens the Admin preferences. |
| `Applications.xlsx` | Applications - all 27 columns, search, mentor-meeting filters, duplicate views |
| `Mentor.xlsx` (+ *Mentor Recommendation Options* sheet) | Mentor Interview - search + category dropdown |
| `Interviews.xlsx` | Interviews - search + Projects Sent / Received |

All `.xlsx` and `.xlsm` files in the folder and its subfolders are checked when
a data page opens. After login, Drive is polled every 60 seconds; a changed
workbook refreshes the visible data page and triggers Calendar synchronization.
Sign Up updates the shared `Users.xlsx`, so the signed-in Google account needs
edit permission for that file. To use another folder, set
`CRM_GOOGLE_DRIVE_FOLDER_ID` in `ui/AdminSet_up/.env`.

Drive and Calendar access use Google OAuth, not the account password. Install
the OAuth desktop-client JSON as `ui/AdminSet_up/credentials.json`, enable both
Google Drive API and Google Calendar API, and authorize `nexuscrmt@gmail.com`
(the sign-in hint is configurable with `CRM_GOOGLE_USER`). Never put an account
password in source code or commit OAuth credentials/token files. See
[`ui/AdminSet_up/SETUP.md`](ui/AdminSet_up/SETUP.md) for the full setup steps.

### Tables

Click a header to sort, drag column edges to resize, scroll sideways for wide
sheets, hover long text for the full value, double-click a row for every field.
Search matches the start of a name or surname ("as" finds *Asiye Turan*).

### Login

Use an account from the shared `Users.xlsx`. The eye icon in the password field
shows or hides what you type. Sign up adds a regular `user` account to it.

### Admin Calendar and Email

Calendar events are generated from these workbook fields:

| Workbook | Source field | Calendar event |
|----------|--------------|----------------|
| `Applications.xlsx` | `Applications Timestamp` | Application received |
| `Mentor.xlsx` (`Mentor` sheet) | `Mentor Date` | Mentor meeting |
| `Interviews.xlsx` | `Project Sent Date`, `Project Received Date` | Project sent / received |

Rows without a parseable date do not create events. Dated application timestamps
keep their time; date-only values become all-day events. Events have stable IDs,
so the app updates them instead of duplicating them. If a source row is removed,
only the corresponding CRM-managed event is deleted. The Admin page loads the
same Calendar after syncing, and supports filtering by event, participant,
email, and status. Contact emails are added to event descriptions and prefilled
in the Mail composer; email is sent only after an admin confirms in that dialog.

The default target is the primary Calendar of the Google account selected during
OAuth. The `/u/2/` in a Calendar browser URL is an account slot, not a Calendar
ID. To target a different calendar, set `CRM_GOOGLE_CALENDAR_ID` to its actual
Calendar ID. Calendar sync requires Drive and Calendar OAuth permissions; sending
email additionally requires SMTP credentials. See
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

## VIT1 / VIT2 comparisons

The Applications page uses a `VIT History` worksheet inside the existing
`Mentor.xlsx`; no extra workbook is needed, and VIT cohort rows stay separate
from mentor conversations. It compares normalized candidate names, shows
previous VIT membership on application records, and lists people found in only
one cohort. The current sample history has 5 VIT1 and 4 VIT2 entries. If the
sheet is absent, the app falls back to `Mentor` rows with explicit VIT1/VIT2
values in `VIT Group` and warns when those cohorts are unavailable.
