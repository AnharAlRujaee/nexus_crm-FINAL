"""NEXUS CRM - PyQt6 interface backed by shared Google Drive workbooks.

Run:
    pip install -r requirements.txt
    python main.py

Project layout:
    main.py                         window controller + navigation
    core/                           Excel data access and filter helpers
    ui/                             shared theme, tables, icons, widgets
    pages/                          application screens
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout

from pages.admin_page import AdminPage
from pages.applications_page import ApplicationsPage
from pages.interviews_page import InterviewsPage
from pages.login_page import LoginPage
from pages.mentor_page import MentorInterviewPage
from pages.preferences_admin_page import PreferencesAdminPage
from pages.preferences_page import PreferencesPage
from pages.signup_page import SignupPage
from core.google_drive import (
    DriveSyncError, POLL_INTERVAL_SECONDS, consume_calendar_sync_request,
    sync_workbooks,
)
from ui.AdminSet_up.calendar_service import CalendarError, sync_events_from_workbooks
from ui.background import FuturisticBackground
from ui.navigation import AnimatedStack
from ui.theme import GLOBAL_STYLE, ui_font
from ui.widgets import Toast


class _DriveSyncWorker(QThread):
    completed = pyqtSignal(bool, str)

    def __init__(self, parent=None, sync_calendar=False):
        super().__init__(parent)
        self._sync_calendar = sync_calendar

    def run(self):
        try:
            changed = sync_workbooks()
            if changed or consume_calendar_sync_request() or self._sync_calendar:
                sync_events_from_workbooks()
        except (DriveSyncError, CalendarError) as exc:
            self.completed.emit(False, str(exc))
        except Exception as exc:
            self.completed.emit(False, f"Unexpected sync error: {exc}")
        else:
            self.completed.emit(changed, "")


class CRMWindow(QMainWindow):
    # Depth decides the slide direction: deeper = forward, shallower = back.
    DEPTH = {
        "login": 0,
        "signup": 1,
        "preferences": 1,
        "preferences_admin": 1,
        "applications": 2,
        "mentor": 2,
        "interviews": 2,
        "admin": 2,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NEXUS CRM")
        self.resize(1280, 840)
        self.setMinimumSize(1100, 740)

        self.username = ""
        self.is_admin = False
        self._current_key = None
        self._closing = False
        self._sync_worker = None

        self.bg = FuturisticBackground()
        self.setCentralWidget(self.bg)
        layout = QVBoxLayout(self.bg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = AnimatedStack()
        layout.addWidget(self.stack)
        self.toast_widget = Toast(self.bg)

        self.pages = {
            "login": LoginPage(self),
            "signup": SignupPage(self),
            "preferences": PreferencesPage(self),
            "preferences_admin": PreferencesAdminPage(self),
            "applications": ApplicationsPage(self),
            "mentor": MentorInterviewPage(self),
            "interviews": InterviewsPage(self),
            "admin": AdminPage(self),
        }
        for key, page in self.pages.items():
            self.stack.add_page(key, page)

        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(POLL_INTERVAL_SECONDS * 1000)
        self._sync_timer.timeout.connect(self._poll_drive)

        self.go("login", animate=False)

    # -- navigation -----------------------------------------------------
    def go(self, key, animate=True):
        if key == self._current_key:
            return
        page = self.pages[key]
        old_depth = self.DEPTH.get(self._current_key, 0) if self._current_key is not None else 0
        direction = 1 if self.DEPTH[key] >= old_depth else -1

        self.bg.set_accent(page.accent)
        page.on_enter()
        self.stack.go(key, direction, animate, page.accent)
        self._current_key = key

    def home_key(self):
        return "preferences_admin" if self.is_admin else "preferences"

    def go_home(self):
        """'Return to Preferences Screen' - admin or regular, depending on login."""
        self.go(self.home_key())

    def login(self, username, is_admin):
        self.username = username
        self.is_admin = is_admin
        self.go_home()
        self._sync_timer.start()
        self._poll_drive(sync_calendar=True)

    def sign_out(self):
        self._sync_timer.stop()
        self.username = ""
        self.is_admin = False
        self.pages["login"].reset()
        self.go("login")

    def account_created(self, username):
        """Sign-up finished: back to login with the new username filled in."""
        self.pages["login"].prefill(username)
        self.go("login")
        self.toast(f"Account '{username}' created \u2014 sign in to continue", self.pages["signup"].accent)

    def toast(self, text, accent):
        self.toast_widget.popup(text, accent)

    def _poll_drive(self, sync_calendar=False):
        if self._sync_worker is not None and self._sync_worker.isRunning():
            return
        current_page = self.pages.get(self._current_key) if self._current_key else None
        if getattr(current_page, "_busy", False):
            return
        worker = _DriveSyncWorker(self, sync_calendar=sync_calendar)
        worker.completed.connect(self._drive_sync_completed)
        worker.finished.connect(worker.deleteLater)
        self._sync_worker = worker
        worker.start()

    def _drive_sync_completed(self, changed, error):
        self._sync_worker = None
        if error:
            self.toast(error, self.pages["applications"].accent)
            return
        if changed and self._current_key in {"applications", "mentor", "interviews", "admin"}:
            self.pages[self._current_key].reload()

    # -- window life-cycle --------------------------------------------------
    def fade_in_window(self):
        self.setWindowOpacity(0.0)
        self._open_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._open_anim.setDuration(600)
        self._open_anim.setStartValue(0.0)
        self._open_anim.setEndValue(1.0)
        self._open_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._open_anim.start()

    def exit_app(self):
        if self._closing:
            return
        self._closing = True
        self._close_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._close_anim.setDuration(260)
        self._close_anim.setStartValue(self.windowOpacity())
        self._close_anim.setEndValue(0.0)
        self._close_anim.finished.connect(self.close)
        self._close_anim.start()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NEXUS CRM")
    app.setStyle("Fusion")
    app.setFont(ui_font(14))
    app.setStyleSheet(GLOBAL_STYLE)

    window = CRMWindow()
    window.show()
    window.fade_in_window()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
