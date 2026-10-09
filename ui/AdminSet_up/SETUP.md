# Admin page setup (Cards 6, 10, 11, 12)

## 1. Install the libraries
From the project root, with the project's virtual environment active:

  python -m pip install -r requirements.txt

## 2. Google Cloud (Card 6)
1. console.cloud.google.com -> create a project (e.g. "CRM_FINAL").
2. APIs & Services -> Library -> search "Google Calendar API" -> Enable.
3. APIs & Services -> OAuth consent screen -> External -> fill app name + your email.
   Under Audience / Test users, add the Gmail account that owns the calendar.
4. APIs & Services -> Credentials -> Create credentials -> OAuth client ID -> Desktop app.
5. Download the JSON, rename it `credentials.json`, and put it next to `calendar_service.py`.
   (A file still named `client_secret_....json` in the same folder is also found automatically.)
  Keep this file private. It is ignored by Git; never commit it or send it in a project archive.
6. Add 2-3 test events in Google Calendar. Invite a test email address as a guest
   (or just type an address in the event description).

## 3. Check it from Python
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
- Sign-in waits 3 minutes for the browser; if you close it, press Event Record again.
- The Google libraries are declared in the project's `requirements.txt`.
- Using the page: press Event Record, click a row, press Mail.
