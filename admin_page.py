"""Page 7 - Admin Menu (admin users only)."""

from PyQt6.QtWidgets import QHBoxLayout, QTableWidget, QVBoxLayout

from ui.base_page import BasePage
from ui.theme import ACCENTS, TEXT, TEXT_FAINT
from ui.widgets import (
    GlassPanel, NeonButton, PageHeader, StatusChip, make_label, style_table,
)


class AdminPage(BasePage):
    HEADERS = ["EVENT", "PARTICIPANT", "DATE", "TIME", "STATUS"]

    def __init__(self, nav):
        super().__init__(nav, ACCENTS["admin"], "admin", "ADMIN MENU")

        header = PageHeader(
            "admin", "Administration", "Admin Menu",
            "Calendar records and participant communication tools.", self.accent)
        header.add_chip(StatusChip("ADMIN ACCESS", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        # Event Record + Mail
        event_btn = NeonButton("Event Record", self.accent, icon="calendar", height=58)
        event_btn.clicked.connect(lambda: self.on_action("Event Record"))
        mail_btn = NeonButton("Mail", self.accent, icon="mail", variant="ghost", height=58)
        mail_btn.clicked.connect(lambda: self.on_action("Mail"))
        self.add_row([event_btn, mail_btn], spacing=10, stretch_end=True)

        # calendar records table
        panel = GlassPanel(self.accent, radius=18)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(18, 16, 18, 12)
        pl.setSpacing(8)
        pl.addWidget(make_label("CALENDAR RECORDS", 12, self.accent, True, 2.6, mono=True))
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        style_table(self.table)
        pl.addWidget(self.table, 1)
        pl.addWidget(make_label(
            "NO CALENDAR RECORDS LOADED \u2014 CALENDAR SYNC ARRIVES IN A LATER STAGE",
            11, TEXT_FAINT, True, 1.2, mono=True))
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
