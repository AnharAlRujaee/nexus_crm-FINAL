"""Page 5 - Mentor Interview."""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout

from ui.base_page import BasePage
from ui.theme import ACCENTS, TEXT, TEXT_DIM
from ui.widgets import (
    GlassPanel, NeonButton, NeonComboBox, NeonLineEdit, PageHeader, StatusChip, WaveWidget,
    make_label,
)


class MentorInterviewPage(BasePage):
    CATEGORIES = [
        "All categories", "Initial contact", "Mentor meeting",
        "Follow-up", "Project discussion", "Needs review",
    ]

    def __init__(self, nav):
        super().__init__(nav, ACCENTS["mentor"], "mentor", "MENTOR INTERVIEW")

        header = PageHeader(
            "mentor", "Module 02", "Mentor Interview",
            "Review conversations and filter them by category.", self.accent)
        header.add_chip(StatusChip("UI PREVIEW", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        # search
        search_panel = GlassPanel(self.accent, radius=16)
        sl = QHBoxLayout(search_panel)
        sl.setContentsMargins(14, 6, 14, 6)
        sl.setSpacing(8)
        self.search = NeonLineEdit("Search conversations\u2026", "search", self.accent)
        sl.addWidget(self.search, 1)
        search_btn = NeonButton("Search", self.accent, icon="search")
        search_btn.clicked.connect(self.on_search)
        self.search.returnPressed.connect(self.on_search)
        sl.addWidget(search_btn)
        self.root.addWidget(search_panel)
        self.reveal(search_panel)

        # actions: all conversations + category dropdown
        actions = GlassPanel(self.accent, radius=16)
        al = QHBoxLayout(actions)
        al.setContentsMargins(14, 6, 18, 6)
        al.setSpacing(14)
        all_btn = NeonButton("All Conversations", self.accent, icon="list")
        all_btn.clicked.connect(self.on_all)
        al.addWidget(all_btn)
        al.addWidget(make_label("CATEGORY", 11, TEXT_DIM, True, 2.2, mono=True))
        self.category = NeonComboBox(self.accent)
        self.category.addItems(self.CATEGORIES)
        self.category.currentTextChanged.connect(self.on_category)
        al.addWidget(self.category, 1)
        self.root.addWidget(actions)
        self.reveal(actions)

        # workspace
        work = GlassPanel(self.accent, radius=18)
        wl = QVBoxLayout(work)
        wl.setContentsMargins(26, 22, 26, 18)
        wl.setSpacing(6)
        wl.addWidget(make_label("CONVERSATION WORKSPACE", 11, self.accent, True, 2.6, mono=True))
        wl.addWidget(make_label("Awaiting conversation data", 20, TEXT, True))
        wl.addWidget(make_label(
            "Search and category controls are ready. Conversation records will stream\n"
            "into this workspace once the data layer is connected in a later stage.",
            13, TEXT_DIM))
        wl.addStretch()
        wl.addWidget(WaveWidget(self.accent))
        self.root.addWidget(work, 1)
        self.reveal(work)

        self.add_row([self.back_button()], stretch_end=True)

    def on_search(self):
        self.nav.toast("Search logic will be connected in a later stage", self.accent)

    def on_all(self):
        self.search.clear()
        self.category.blockSignals(True)
        self.category.setCurrentIndex(0)
        self.category.blockSignals(False)
        self.nav.toast("Showing all conversations (preview)", self.accent)

    def on_category(self, text):
        if self.isVisible():
            self.nav.toast(f"Category filter: {text}", self.accent)
