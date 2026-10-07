"""Page 5 - Mentor Interview (loaded from data/Mentor.xlsx)."""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout

from data_service import load_mentor, load_mentor_recommendations, name_matches
from ui.base_page import BasePage
from ui.theme import ACCENTS, TEXT_DIM
from ui.widgets import (
    DataTable, GlassPanel, NeonButton, NeonComboBox, NeonLineEdit, PageHeader, StatusChip,
    make_label,
)


class MentorInterviewPage(BasePage):
    def __init__(self, nav):
        super().__init__(nav, ACCENTS["mentor"], "mentor", "MENTOR INTERVIEW")
        self.table_data = None
        self.recommendations = []

        header = PageHeader(
            "mentor", "Module 02", "Mentor Interview",
            "Search conversations and filter by recommendation from Mentor.xlsx.", self.accent)
        header.add_chip(StatusChip("LIVE DATA", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        search_panel = GlassPanel(self.accent, radius=16)
        sl = QHBoxLayout(search_panel)
        sl.setContentsMargins(14, 6, 14, 6)
        sl.setSpacing(8)
        self.search = NeonLineEdit("Search by candidate name or surname prefix…", "search", self.accent)
        sl.addWidget(self.search, 1)
        search_btn = NeonButton("Search", self.accent, icon="search")
        search_btn.clicked.connect(self.refresh)
        self.search.returnPressed.connect(self.refresh)
        sl.addWidget(search_btn)
        self.root.addWidget(search_panel)
        self.reveal(search_panel)

        actions = GlassPanel(self.accent, radius=16)
        al = QHBoxLayout(actions)
        al.setContentsMargins(14, 6, 18, 6)
        al.setSpacing(14)
        all_btn = NeonButton("All Conversations", self.accent, icon="list")
        all_btn.clicked.connect(self.on_all)
        al.addWidget(all_btn)
        al.addWidget(make_label("RECOMMENDATION", 11, TEXT_DIM, True, 2.2, mono=True))
        self.category = NeonComboBox(self.accent)
        self.category.addItem("All recommendations")
        self.category.currentTextChanged.connect(self.refresh)
        al.addWidget(self.category, 1)
        self.root.addWidget(actions)
        self.reveal(actions)

        table_panel = GlassPanel(self.accent, radius=18)
        tl = QVBoxLayout(table_panel)
        tl.setContentsMargins(10, 10, 10, 8)
        tl.setSpacing(6)
        self.table = DataTable()
        tl.addWidget(self.table, 1)
        self.count = make_label("", 11, TEXT_DIM, True, 1.4, mono=True)
        tl.addWidget(self.count)
        self.root.addWidget(table_panel, 1)
        self.reveal(table_panel)

        self.add_row([self.back_button()], stretch_end=True)

    def on_enter(self):
        super().on_enter()
        self.reload()

    def reload(self):
        try:
            self.table_data = load_mentor()
            recs = load_mentor_recommendations()
        except Exception as exc:
            self.table_data = None
            self.table.load(["Error"], [[str(exc)]])
            self.count.setText("COULD NOT LOAD MENTOR.XLSX")
            return
        current = self.category.currentText()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("All recommendations")
        self.category.addItems(recs)
        idx = self.category.findText(current)
        self.category.setCurrentIndex(max(0, idx))
        self.category.blockSignals(False)
        self.refresh()

    def on_all(self):
        self.search.clear()
        self.category.blockSignals(True)
        self.category.setCurrentIndex(0)
        self.category.blockSignals(False)
        self.refresh()

    def refresh(self, *_args):
        if self.table_data is None:
            return
        rows = list(self.table_data.rows)
        rec_i = self.table_data.col("Recommendation")
        chosen = self.category.currentText()
        if rec_i is not None and chosen and chosen != "All recommendations":
            rows = [r for r in rows if r[rec_i] == chosen]
        query = self.search.text()
        name_i = self.table_data.name_index()
        if query.strip():
            rows = [r for r in rows if name_matches(r[name_i], query)]
        self.table.load(self.table_data.headers, rows, self.accent)
        self.count.setText(
            f"SHOWING {len(rows)} CONVERSATION{'S' if len(rows) != 1 else ''}  ·  "
            f"{len(self.table_data.rows)} IN MENTOR.XLSX"
        )
