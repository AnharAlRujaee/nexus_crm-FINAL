"""Page 4 - Applications."""

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QHBoxLayout, QTableWidget, QTableWidgetItem, QVBoxLayout

from ui.base_page import BasePage
from ui.theme import ACCENTS, BAD, OK, TEXT_DIM, TEXT_FAINT, WARN
from ui.widgets import (
    GlassPanel, NeonButton, NeonLineEdit, PageHeader, StatusChip, make_label, style_table,
)

STATUS_COLORS = {"Accepted": OK, "Pending": WARN, "Rejected": BAD}


class ApplicationsPage(BasePage):
    HEADERS = ["ID", "APPLICANT", "EMAIL", "POSITION", "STATUS", "MENTOR MEETING", "DATE APPLIED"]

    # Sample rows so the layout can be judged; real data arrives in a later stage.
    ROWS = [
        [1, "Sara Cohen", "sara.cohen@example.com", "Backend Developer", "Pending", "2026-10-12 10:00", "2026-09-02"],
        [2, "Omar Hassan", "omar.hassan@example.com", "Data Analyst", "Accepted", "2026-10-08 14:30", "2026-09-05"],
        [3, "Lena Fischer", "lena.fischer@example.com", "UX Designer", "Pending", None, "2026-09-07"],
        [4, "Mark Evans", "mark.evans@example.com", "Frontend Developer", "Rejected", None, "2026-09-09"],
        [5, "Aisha Khan", "aisha.khan@example.com", "Backend Developer", "Pending", "2026-10-15 09:00", "2026-09-10"],
        [6, "Tom de Vries", "tom.devries@example.com", "DevOps Engineer", "Pending", None, "2026-09-12"],
    ]

    def __init__(self, nav):
        super().__init__(nav, ACCENTS["applications"], "applications", "APPLICATIONS")
        self.mode = "all"

        header = PageHeader(
            "apps", "Module 01", "Application pipeline",
            "Search and preview application records.", self.accent)
        header.add_chip(StatusChip("DATA PREVIEW", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        # search bar
        search_panel = GlassPanel(self.accent, radius=16)
        sl = QHBoxLayout(search_panel)
        sl.setContentsMargins(14, 6, 14, 6)
        sl.setSpacing(8)
        self.search = NeonLineEdit("Search by name, email, position or status\u2026", "search", self.accent)
        sl.addWidget(self.search, 1)
        search_btn = NeonButton("Search", self.accent, icon="search")
        search_btn.clicked.connect(self.refresh)
        self.search.returnPressed.connect(self.refresh)
        sl.addWidget(search_btn)
        self.root.addWidget(search_panel)
        self.reveal(search_panel)

        # filter buttons
        self.filter_buttons = []
        for text, mode, icon in (
            ("All Applications", "all", "list"),
            ("Mentor Meeting Defined", "defined", "check"),
            ("Mentor Meeting Not Defined", "not_defined", "cross"),
        ):
            b = NeonButton(text, self.accent, icon=icon, variant="ghost", height=42)
            b.setCheckable(True)
            b.clicked.connect(lambda _checked=False, m=mode: self.set_mode(m))
            self.filter_buttons.append((b, mode))
        self.filter_buttons[0][0].setChecked(True)
        self.add_row([b for b, _ in self.filter_buttons], stretch_end=True)

        # table
        table_panel = GlassPanel(self.accent, radius=18)
        tl = QVBoxLayout(table_panel)
        tl.setContentsMargins(14, 14, 14, 10)
        tl.setSpacing(6)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        style_table(self.table)
        tl.addWidget(self.table, 1)
        self.count = make_label("", 11, TEXT_DIM, True, 1.4, mono=True)
        tl.addWidget(self.count)
        self.root.addWidget(table_panel, 1)
        self.reveal(table_panel)

        self.add_row([self.back_button()], stretch_end=True)
        self.refresh()

    def set_mode(self, mode):
        self.mode = mode
        for b, m in self.filter_buttons:
            b.setChecked(m == mode)
        self.refresh()

    def refresh(self):
        query = self.search.text().strip().lower()
        data = []
        for row in self.ROWS:
            has_meeting = row[5] is not None
            if self.mode == "defined" and not has_meeting:
                continue
            if self.mode == "not_defined" and has_meeting:
                continue
            haystack = " ".join(str(x) for x in row if x is not None).lower()
            if query and query not in haystack:
                continue
            data.append(row)

        self.table.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, value in enumerate(row):
                item = QTableWidgetItem("Not set" if value is None else str(value))
                if value is None:
                    item.setForeground(QBrush(QColor(TEXT_FAINT)))
                elif c == 4:
                    item.setForeground(QBrush(QColor(STATUS_COLORS.get(value, TEXT_DIM))))
                self.table.setItem(r, c, item)
        self.count.setText(f"SHOWING {len(data)} OF {len(self.ROWS)} APPLICATIONS")
