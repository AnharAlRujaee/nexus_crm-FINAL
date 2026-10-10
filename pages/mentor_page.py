"""Page 5 - Mentor Interview (data from data/Mentor.xlsx)."""

from PyQt6.QtWidgets import QHBoxLayout

from core import filters
from core.data_store import DataError, Table, load_mentor, load_mentor_options
from ui.base_page import BasePage
from ui.data_table import RecordDialog, build_table_panel, set_status
from ui.theme import ACCENTS, BAD, OK, TEXT_DIM, WARN
from ui.widgets import (
    GlassPanel, NeonButton, NeonComboBox, NeonLineEdit, PageHeader, StatusChip, make_label,
)

ALL_CATEGORIES = "All categories"
CENTERED = ("VIT Group", "Score", "Secondary Score")


class MentorInterviewPage(BasePage):
    def __init__(self, nav):
        super().__init__(nav, ACCENTS["mentor"], "mentor", "MENTOR INTERVIEW")
        self.table_data = Table([], [])
        self.error = ""
        self.i_candidate = self.i_mentor = self.i_rec = self.i_alt = -1

        header = PageHeader(
            "mentor", "Module 02", "Mentor Interview",
            "Review mentor conversations and filter them by recommendation.", self.accent)
        header.add_chip(StatusChip("ONEDRIVE SYNC", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        # search
        search_panel = GlassPanel(self.accent, radius=16)
        sl = QHBoxLayout(search_panel)
        sl.setContentsMargins(14, 6, 14, 6)
        sl.setSpacing(8)
        self.search = NeonLineEdit(
            "Search by candidate or mentor name \u2014 e.g. \u201cas\u201d", "search", self.accent)
        sl.addWidget(self.search, 1)
        search_btn = NeonButton("Search", self.accent, icon="search")
        search_btn.clicked.connect(lambda: self.refresh())
        self.search.returnPressed.connect(lambda: self.refresh())
        self.search.textChanged.connect(lambda _text: self.refresh())
        sl.addWidget(search_btn)
        self.root.addWidget(search_panel)
        self.reveal(search_panel)

        # actions: all conversations + recommendation dropdown
        actions = GlassPanel(self.accent, radius=16)
        al = QHBoxLayout(actions)
        al.setContentsMargins(14, 6, 18, 6)
        al.setSpacing(14)
        all_btn = NeonButton("All Conversations", self.accent, icon="list")
        all_btn.clicked.connect(self.on_all)
        al.addWidget(all_btn)
        al.addWidget(make_label("CATEGORY", 11, TEXT_DIM, True, 2.2, mono=True))
        self.category = NeonComboBox(self.accent)
        self.category.addItem(ALL_CATEGORIES)
        self.category.currentIndexChanged.connect(lambda _i: self.refresh())
        al.addWidget(self.category, 1)
        self.root.addWidget(actions)
        self.reveal(actions)

        # table
        panel, self.table, self.status = build_table_panel(self.accent)
        self.table.record_activated.connect(self.show_record)
        self.root.addWidget(panel, 1)
        self.reveal(panel)

        self.add_row([self.back_button()], stretch_end=True)

    # ------------------------------------------------------------------
    def on_enter(self):
        self.reload()
        super().on_enter()

    def reload(self):
        try:
            self.table_data = load_mentor()
            self.error = ""
        except DataError as exc:
            self.table_data = Table([], [])
            self.error = str(exc)
        t = self.table_data
        self.i_candidate = t.index("Candidate Name")
        self.i_mentor = t.index("Mentor Name")
        self.i_rec = t.index("Recommendation")
        self.i_alt = t.index("Alternative Recommendation")
        self._load_categories()
        self.refresh()

    def _load_categories(self):
        """Fill the dropdown from the 'Mentor Recommendation Options' sheet."""
        try:
            options = load_mentor_options()
        except DataError:
            # fall back to whatever recommendations actually occur in the data
            options = sorted({str(r[self.i_rec]) for r in self.table_data.rows
                              if self.i_rec >= 0 and r[self.i_rec]})
        current = self.category.currentText()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem(ALL_CATEGORIES)
        self.category.addItems(options)
        index = self.category.findText(current)
        self.category.setCurrentIndex(index if index >= 0 else 0)
        self.category.blockSignals(False)

    def on_all(self):
        """All Conversations: clear the search and the category, show everything."""
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.category.blockSignals(True)
        self.category.setCurrentIndex(0)
        self.category.blockSignals(False)
        self.refresh()

    def refresh(self):
        t = self.table_data
        query = self.search.text()
        category = self.category.currentText() if self.category.currentIndex() > 0 else None

        shown = []
        for i, row in enumerate(t.rows):
            if query.strip():
                candidate = row[self.i_candidate] if self.i_candidate >= 0 else None
                mentor = row[self.i_mentor] if self.i_mentor >= 0 else None
                if not filters.name_matches(query, candidate, mentor):
                    continue
            if category:
                rec = row[self.i_rec] if self.i_rec >= 0 else None
                alt = row[self.i_alt] if self.i_alt >= 0 else None
                if not (filters.same_option(category, rec) or filters.same_option(category, alt)):
                    continue
            shown.append(i)

        self.table.set_data(
            t.headers, [t.rows[i] for i in shown], indices=shown,
            chip_fn=self._chip, center=CENTERED,
            max_widths={"Notes": 340, "Recommendation": 330, "Alternative Recommendation": 330})

        if self.error:
            set_status(self.status, "\u26A0  " + self.error.upper(), BAD)
        else:
            set_status(
                self.status,
                f"SHOWING {len(shown)} OF {len(t.rows)} CONVERSATIONS   \u00B7   "
                f"CLICK A HEADER TO SORT   \u00B7   DOUBLE-CLICK A ROW FOR FULL NOTES")

    def _chip(self, header, value):
        """Score chip: green 8+, amber 5-7, red below 5."""
        if header == "Score" and isinstance(value, (int, float)):
            color = OK if value >= 8 else WARN if value >= 5 else BAD
            return (str(value), color)
        return None

    def show_record(self, index):
        t = self.table_data
        if not 0 <= index < len(t.rows):
            return
        row = t.rows[index]
        name = row[self.i_candidate] if self.i_candidate >= 0 and row[self.i_candidate] else "Conversation"
        RecordDialog("Mentor conversation", str(name).title(), t.headers, row,
                     self.accent, self.window()).exec()
