# Admin page setup (Cards 6, 10, 11, 12)

## 1. Install the libraries
From the project root, with the project's virtual environment active:

  python -m pip install -r requirements.txt

## 2. Google Cloud (Drive and Calendar)
1. console.cloud.google.com -> create a project (e.g. "CRM_FINAL").
2. Enable both Google Drive API and Google Calendar API.
3. Set up the OAuth consent screen and add `nexuscrmt@gmail.com` as a test user
  if the app is in Testing mode.
4. Create an OAuth client ID of type Desktop app.
5. Download its JSON as `credentials.json` next to `calendar_service.py`.
   (A file still named `client_secret_....json` in the same folder is also found automatically.)
  Keep this file private. It is ignored by Git; never commit it or share it.
6. Copy `.env.example` to `.env`. Set `CRM_GOOGLE_USER=nexuscrmt@gmail.com` to
  preselect the owner account during OAuth. The account must have access to the
  Drive folder; it needs edit access to `Users.xlsx` for Sign Up.
7. The supplied Calendar URL's `/u/2/` identifies an account slot in the browser,
  not a Calendar ID. The app uses that OAuth account's `primary` calendar. Set
  `CRM_GOOGLE_CALENDAR_ID` to the actual Calendar ID only if a non-primary
  calendar should be used.

The first OAuth sign-in requests Drive read/write and Calendar event permissions.
Because the existing token was created with narrower permissions, remove
`ui/AdminSet_up/token.json` once and sign in again as the owner account.

Applications submission timestamps, Mentor Date values and Interviews project
sent/received dates are synced as managed Calendar events. Dates without a time
become all-day events; application timestamps keep their time. Existing events
are updated in place; events managed by CRM are removed if the source row is
deleted. The Admin page then loads events from this same Calendar.

Workbook pages check the folder when opened. After login, the app also polls
every 60 seconds and syncs Calendar when Drive reports a workbook change.

## 3. Check Calendar access from Python
    cd <folder with calendar_service.py>
    python test_calendar.py
First run opens a browser to sign in and creates `token.json`.
"Google hasn't verified this app" -> Advanced -> continue (normal for test apps).

## 4. Email (Card 12)
The archive includes `.env.example` next to `mailer.py`. Copy it to `.env` and
replace both placeholders with your own Gmail address and Gmail App Password.
Alternatively run `bash run_setup.sh` from this directory; it prompts for those
values and writes `.env` without displaying the password.

    CRM_SMTP_USER=your-address@gmail.com
    CRM_SMTP_PASSWORD=your-16-char-app-password

These example values are placeholders and will not authenticate until replaced.

Gmail needs 2-Step Verification on, then an App Password
(myaccount.google.com -> Security -> App passwords). Your normal password will not work.

    python test_mail.py some.test.address@example.com

## 5. Keep secrets out of git
The project `.gitignore` excludes OAuth credentials, OAuth tokens, and `.env` files.

## Notes
- `pages/admin_page.py` imports `ui.AdminSet_up.calendar_service` and `ui.AdminSet_up.mailer`.
- OAuth sign-in waits 3 minutes for the browser; if you close it, press Event Record again.
- The Google libraries are declared in the project's `requirements.txt`.
- Using the page: press Event Record, click a row, press Mail.
