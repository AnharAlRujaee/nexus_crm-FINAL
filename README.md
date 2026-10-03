# NEXUS CRM — Futuristic PyQt6 Interface

UI-only stage of the CRM capstone: every window is built, styled, animated and
fully navigable. No Google Drive / Calendar / email / real search yet.

## Run

```bash
pip install -r requirements.txt     # or: pip install PyQt6
python main.py
```

## Project layout

```
main.py                          window controller + navigation logic
ui/
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

### Sign up

Login card → **Sign up** → fill the form (email format, 8+ character password,
matching confirmation, live strength meter) → returns to Login with the username
pre-filled. UI preview only: accounts are not stored yet.

### Login

- Any non-empty username + password signs in as a normal user.
- Username `admin` (any non-empty password) previews Admin mode.
  This is a UI preview only; real authentication comes in a later stage.

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

Google Drive, Google Calendar API, real data source, production search/filter
backend, email sending.
