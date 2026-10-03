"""Page 6 - Interviews."""

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ui.base_page import BasePage
from ui.theme import ACCENTS, TEXT_FAINT
from ui.widgets import (
    GlassPanel, NavCard, NeonButton, NeonLineEdit, PageHeader, StatusChip, make_label,
)


class InterviewsPage(BasePage):
    def __init__(self, nav):
        super().__init__(nav, ACCENTS["interviews"], "interviews", "INTERVIEWS")

        header = PageHeader(
            "interviews", "Module 03", "Interviews",
            "Track the project exchange stages.", self.accent)
        header.add_chip(StatusChip("UI PREVIEW", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        # search
        search_panel = GlassPanel(self.accent, radius=16)
        sl = QHBoxLayout(search_panel)
        sl.setContentsMargins(14, 6, 14, 6)
        sl.setSpacing(8)
        self.search = NeonLineEdit("Search interviews\u2026", "search", self.accent)
        sl.addWidget(self.search, 1)
        search_btn = NeonButton("Search", self.accent, icon="search")
        search_btn.clicked.connect(self.on_search)
        self.search.returnPressed.connect(self.on_search)
        sl.addWidget(search_btn)
        self.root.addWidget(search_panel)
        self.reveal(search_panel)

        self.root.addStretch(1)

        # Project Sent / Project Received
        cards = QWidget()
        row = QHBoxLayout(cards)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        sent = NavCard("upload", "Project Sent", "Projects sent out to participants.",
                       self.accent, "OUT", "VIEW SENT")
        received = NavCard("download", "Project Received", "Projects received back for review.",
                           self.accent, "IN", "VIEW RECEIVED")
        sent.clicked.connect(lambda: self.on_action("Project Sent"))
        received.clicked.connect(lambda: self.on_action("Project Received"))
        row.addWidget(sent)
        row.addWidget(received)
        self.root.addWidget(cards)
        self.reveal(sent, received)

        self.root.addStretch(1)

        self.root.addWidget(make_label(
            "Project send / receive actions will be connected in a later stage.",
            12, TEXT_FAINT))
        self.add_row([self.back_button()], stretch_end=True)

    def on_search(self):
        self.nav.toast("Search logic will be connected in a later stage", self.accent)

    def on_action(self, name):
        self.nav.toast(f"{name} \u2014 action will be connected in a later stage", self.accent)
