# NEXUS CRM — Futuristic PyQt6 Interface

CRM capstone: every window is built, styled, animated and navigable, and the
Applications, Mentor Interview, Interviews and Login pages now run on the real
Excel workbooks in `data/`. Google Calendar / e-mail (Admin menu) come later.

## Run

```bash
pip install -r requirements.txt     # PyQt6 + openpyxl
python main.py
```

## Project layout

```
main.py                          window controller + navigation logic
core/
  data_store.py                  reads the .xlsx files (and saves new sign-ups)
  filters.py                     search / duplicate / category matching
ui/
  data_table.py                  sortable, scrollable data table + record dialog
  theme.py                       colours, fonts, global stylesheet
  icons.py                       vector icons drawn in code (no image files)
  background.py                  animated aurora / grid / particle background
  widgets.py                     glow buttons, glass panels, nav cards, toasts...
  navigation.py                  animated page transitions (slide + fade + light beam)
  base_page.py                   shared page skeleton + staggered reveal
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

### Data (`data/`)

| File | Used by |
|------|---------|
| `Users.xlsx` (Username, Password, Role) | Login / Sign up. Role `admin` opens the Admin preferences. |
| `Applications.xlsx` | Applications - all 27 columns, search, mentor-meeting filters, duplicate views |
| `Mentor.xlsx` (+ *Mentor Recommendation Options* sheet) | Mentor Interview - search + category dropdown |
| `Interviews.xlsx` | Interviews - search + Projects Sent / Received |

Edit a workbook, then reopen the page: data is re-read every time a page opens.
Close Excel before signing up a new user (the file must be writable).
When packaged as an .exe, keep the `data/` folder next to it.

### Tables

Click a header to sort, drag column edges to resize, scroll sideways for wide
sheets, hover long text for the full value, double-click a row for every field.
Search matches the start of a name or surname ("as" finds *Asiye Turan*).

### Login

Use an account from `Users.xlsx`. The eye icon in the password field shows or
hides what you type. Sign up adds a regular `user` account to `Users.xlsx`.

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

Google Drive sync, Google Calendar API and email sending (Admin menu), plus the
VIT1 / VIT2 comparison filters (those workbooks are not in the project yet).
