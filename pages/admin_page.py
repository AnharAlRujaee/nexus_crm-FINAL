"""Page 7 - Admin Menu (admin users only)."""

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QPlainTextEdit, QVBoxLayout,
)

from ui.AdminSet_up.calendar_service import CalendarError, fetch_events
from ui.AdminSet_up.mailer import MailError, is_valid_address, send_emails
from ui.base_page import BasePage
from ui.data_table import DataTable, ROW_ROLE
from ui.theme import ACCENTS, BAD, OK, TEXT, TEXT_FAINT, WARN, page_style
from ui.widgets import (
    GlassPanel, NeonButton, NeonLineEdit, PageHeader, StatusChip, make_label,
)

EVENT_ROLE = int(Qt.ItemDataRole.UserRole.value) + 20


class _Worker(QThread):
    """Runs a blocking call (Google / SMTP) off the UI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            result = self._fn()
        except (CalendarError, MailError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # never let a worker crash the app
            self.failed.emit(f"Unexpected error: {exc}")
        else:
            self.succeeded.emit(result)


class ComposeMailDialog(QDialog):
    def __init__(self, accent, recipients, subject, body, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Send Email")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setStyleSheet(
            page_style(accent)
            + f"QDialog {{ background: #070C1C; }}"
            + f"QPlainTextEdit {{ background: rgba(6, 11, 28, 200); color: {TEXT};"
              f" border: 1px solid rgba(110, 140, 230, 70); border-radius: 13px;"
              f" padding: 10px 14px; font-size: 14px; }}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 16)
        lay.setSpacing(10)
        lay.addWidget(make_label("SEND EMAIL", 12, accent, True, 2.6, mono=True))

        self.to_edit = NeonLineEdit("Recipients (comma separated)", "mail", accent)
        self.to_edit.setText(", ".join(recipients))
        self.subject_edit = NeonLineEdit("Subject", None, accent)
        self.subject_edit.setText(subject)
        self.body_edit = QPlainTextEdit()
        self.body_edit.setPlainText(body)
        self.body_edit.setMinimumHeight(160)
        lay.addWidget(self.to_edit)
        lay.addWidget(self.subject_edit)
        lay.addWidget(self.body_edit, 1)

        self.error_label = make_label("", 12, BAD, True)
        lay.addWidget(self.error_label)

        cancel = NeonButton("Cancel", accent, variant="ghost")
        cancel.clicked.connect(self.reject)
        send = NeonButton("Send", accent, icon="arrow")
        send.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(send)
        lay.addLayout(row)

    def accept(self):
        if not self.recipients():
            self.error_label.setText("Enter at least one recipient")
        elif not all(is_valid_address(a) for a in self.recipients()):
            self.error_label.setText("One of the addresses is not valid")
        elif not self.subject_edit.text().strip():
            self.error_label.setText("Subject is empty")
        else:
            super().accept()

    def recipients(self):
        return [a.strip() for a in self.to_edit.text().replace(";", ",").split(",") if a.strip()]

    def values(self):
        return self.recipients(), self.subject_edit.text().strip(), self.body_edit.toPlainText()


class AdminPage(BasePage):
    HEADERS = ["EVENT", "PARTICIPANT", "DATE", "TIME", "STATUS"]

    def __init__(self, nav):
        super().__init__(nav, ACCENTS["admin"], "admin", "ADMIN MENU")
        self._busy = False
        self._worker = None
        self._events = []

        header = PageHeader(
            "admin", "Administration", "Admin Menu",
            "Calendar records and participant communication tools.", self.accent)
        header.add_chip(StatusChip("ADMIN ACCESS", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        # Event Record + Mail
        self.event_btn = NeonButton("Event Record", self.accent, icon="calendar", height=58)
        self.event_btn.clicked.connect(self.on_event_record)
        self.mail_btn = NeonButton("Mail", self.accent, icon="mail", variant="ghost", height=58)
        self.mail_btn.clicked.connect(self.on_mail)
        self.add_row([self.event_btn, self.mail_btn], spacing=10, stretch_end=True)

        # calendar records table
        panel = GlassPanel(self.accent, radius=18)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(18, 16, 18, 12)
        pl.setSpacing(8)
        pl.addWidget(make_label("CALENDAR RECORDS", 12, self.accent, True, 2.6, mono=True))
        self.table = DataTable(self.accent)
        self.table.set_data(self.HEADERS, [])
        pl.addWidget(self.table, 1)
        self.status_label = make_label(
            "NO CALENDAR RECORDS LOADED \u2014 PRESS EVENT RECORD TO LOAD THEM",
            11, TEXT_FAINT, True, 1.2, mono=True)
        pl.addWidget(self.status_label)
        self.root.addWidget(panel, 1)
        self.reveal(panel)

        # footer: return to admin preferences + exit
        back = NeonButton("Preferences \u2014 Return to Admin Screen", self.accent,
                          icon="back", variant="ghost")
        back.clicked.connect(lambda: self.nav.go("preferences_admin"))
        exit_btn = NeonButton("Exit", self.accent, icon="power")
        exit_btn.clicked.connect(self.nav.exit_app)
        footer = self.add_row([back], spacing=10)
        footer.layout().addStretch()
        footer.layout().addWidget(exit_btn)

    def on_action(self, name):
        self.nav.toast(f"{name} \u2014 will be connected in a later stage", self.accent)

    # -- background work ----------------------------------------------------
    def _run(self, fn, on_ok, on_fail):
        self._busy = True
        self.event_btn.setEnabled(False)
        self.mail_btn.setEnabled(False)
        worker = _Worker(fn, self)
        worker.succeeded.connect(on_ok)
        worker.failed.connect(on_fail)
        worker.finished.connect(self._run_finished)
        self._worker = worker
        worker.start()

    def _run_finished(self):
        self._busy = False
        self.event_btn.setEnabled(True)
        self.mail_btn.setEnabled(True)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    # -- Event Record -------------------------------------------------------
    def on_event_record(self):
        if self._busy:
            return
        self.status_label.setText("LOADING CALENDAR EVENTS\u2026")
        self._run(fetch_events, self._events_loaded, self._events_failed)

    def _events_loaded(self, events):
        self._events = list(events)
        rows = [[event["title"], event["participants"], event["date"],
                 event["time"], event["status"]] for event in self._events]
        self.table.set_data(self.HEADERS, rows, indices=range(len(rows)))
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            source_index = item.data(ROW_ROLE)
            item.setData(EVENT_ROLE, self._events[source_index])

        if self._events:
            self.status_label.setText(f"{len(self._events)} CALENDAR EVENTS LOADED")
            self.nav.toast(f"{len(self._events)} events loaded", OK)
        else:
            self.status_label.setText("NO EVENTS FOUND IN THE CALENDAR")
            self.nav.toast("No events found in the calendar", WARN)

    def _events_failed(self, message):
        self.status_label.setText("COULD NOT LOAD CALENDAR EVENTS")
        self.nav.toast(message, BAD)

    # -- Mail ---------------------------------------------------------------
    def on_mail(self):
        if self._busy:
            return
        row = self.table.currentRow()
        if row < 0:
            self.nav.toast("Select an event in the table first", WARN)
            return
        event = self.table.item(row, 0).data(EVENT_ROLE) or {}
        emails = event.get("emails", [])
        if not emails:
            self.nav.toast("This event has no email address", WARN)
            return

        subject = f"Regarding: {event['title']}"
        body = (f"Hello,\n\nThis is a message about \"{event['title']}\" "
                f"on {event['date']} at {event['time']}.\n\n")

        dialog = ComposeMailDialog(self.accent, emails, subject, body, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        recipients, subject, body = dialog.values()
        self._run(lambda: send_emails(recipients, subject, body),
                  lambda result: self._mail_sent(result, len(recipients)),
                  self._mail_failed)

    def _mail_sent(self, result, total):
        sent, failures = result
        if not failures:
            self.nav.toast(f"Email sent to {sent} recipient(s)", OK)
        else:
            names = ", ".join(a for a, _ in failures)
            self.nav.toast(f"Sent {sent}/{total} \u2014 failed: {names}", WARN)

    def _mail_failed(self, message):
        self.nav.toast(message, BAD)
