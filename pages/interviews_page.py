"""Page 6 - Interviews (loaded from data/Interviews.xlsx)."""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout

from data_service import is_blank, load_interviews, name_matches
from ui.base_page import BasePage
from ui.theme import ACCENTS, TEXT_DIM
from ui.widgets import (
    DataTable, GlassPanel, NeonButton, NeonLineEdit, PageHeader, StatusChip, make_label,
)


class InterviewsPage(BasePage):
    def __init__(self, nav):
        super().__init__(nav, ACCENTS["interviews"], "interviews", "INTERVIEWS")
        self.mode = "all"
        self.table_data = None

        header = PageHeader(
            "interviews", "Module 03", "Interviews",
            "Track project sent and received dates from Interviews.xlsx.", self.accent)
        header.add_chip(StatusChip("LIVE DATA", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        search_panel = GlassPanel(self.accent, radius=16)
        sl = QHBoxLayout(search_panel)
        sl.setContentsMargins(14, 6, 14, 6)
        sl.setSpacing(8)
        self.search = NeonLineEdit("Search by name or surname prefix…", "search", self.accent)
        sl.addWidget(self.search, 1)
        search_btn = NeonButton("Search", self.accent, icon="search")
        search_btn.clicked.connect(self.refresh)
        self.search.returnPressed.connect(self.refresh)
        sl.addWidget(search_btn)
        self.root.addWidget(search_panel)
        self.reveal(search_panel)

        self.filter_buttons = []
        for text, mode, icon in (
            ("All Interviews", "all", "list"),
            ("Projects Sent", "sent", "upload"),
            ("Projects Received", "received", "download"),
        ):
            b = NeonButton(text, self.accent, icon=icon, variant="ghost", height=42)
            b.setCheckable(True)
            b.clicked.connect(lambda _checked=False, m=mode: self.set_mode(m))
            self.filter_buttons.append((b, mode))
        self.filter_buttons[0][0].setChecked(True)
        self.add_row([b for b, _ in self.filter_buttons], stretch_end=True)

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
            self.table_data = load_interviews()
        except Exception as exc:
            self.table_data = None
            self.table.load(["Error"], [[str(exc)]])
            self.count.setText("COULD NOT LOAD INTERVIEWS.XLSX")
            return
        self.refresh()

    def set_mode(self, mode):
        self.mode = mode
        for b, m in self.filter_buttons:
            b.setChecked(m == mode)
        self.refresh()

    def refresh(self):
        if self.table_data is None:
            return
        rows = list(self.table_data.rows)
        sent_i = self.table_data.col("Project Sent Date")
        recv_i = self.table_data.col("Project Received Date")
        if self.mode == "sent" and sent_i is not None:
            rows = [r for r in rows if not is_blank(r[sent_i])]
        elif self.mode == "received" and recv_i is not None:
            rows = [r for r in rows if not is_blank(r[recv_i])]
        query = self.search.text()
        name_i = self.table_data.name_index()
        if query.strip():
            rows = [r for r in rows if name_matches(r[name_i], query)]
        self.table.load(self.table_data.headers, rows, self.accent)
        self.count.setText(
            f"SHOWING {len(rows)} RECORD{'S' if len(rows) != 1 else ''}  ·  "
            f"{len(self.table_data.rows)} IN INTERVIEWS.XLSX"
        )
