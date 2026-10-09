"""Page 6 - Interviews (data from data/Interviews.xlsx)."""

from PyQt6.QtWidgets import QHBoxLayout

from core import filters
from core.data_store import DataError, Table, load_interviews
from ui.base_page import BasePage
from ui.data_table import RecordDialog, build_table_panel, set_status
from ui.theme import ACCENTS, BAD, WARN
from ui.widgets import (
    GlassPanel, NeonButton, NeonLineEdit, PageHeader, StatusChip,
)


class InterviewsPage(BasePage):
    def __init__(self, nav):
        super().__init__(nav, ACCENTS["interviews"], "interviews", "INTERVIEWS")
        self.mode = "all"
        self.table_data = Table([], [])
        self.error = ""
        self.i_name = self.i_sent = self.i_received = -1

        header = PageHeader(
            "interviews", "Module 03", "Interviews",
            "Track the project exchange stages.", self.accent)
        header.add_chip(StatusChip("ONEDRIVE SYNC", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        # search
        search_panel = GlassPanel(self.accent, radius=16)
        sl = QHBoxLayout(search_panel)
        sl.setContentsMargins(14, 6, 14, 6)
        sl.setSpacing(8)
        self.search = NeonLineEdit("Search by name or surname \u2014 e.g. \u201cas\u201d", "search", self.accent)
        sl.addWidget(self.search, 1)
        search_btn = NeonButton("Search", self.accent, icon="search")
        search_btn.clicked.connect(lambda: self.refresh())
        self.search.returnPressed.connect(lambda: self.refresh())
        self.search.textChanged.connect(lambda _text: self.refresh())
        sl.addWidget(search_btn)
        self.root.addWidget(search_panel)
        self.reveal(search_panel)

        # Project Sent / Project Received filters
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

        # table
        panel, self.table, self.status = build_table_panel(self.accent)
        self.table.record_activated.connect(self.show_record)
        self.root.addWidget(panel, 1)
        self.reveal(panel)

        self.add_row([self.back_button()], stretch_end=True)
        self.reload()

    # ------------------------------------------------------------------
    def on_enter(self):
        self.reload()
        super().on_enter()

    def reload(self):
        try:
            self.table_data = load_interviews()
            self.error = ""
        except DataError as exc:
            self.table_data = Table([], [])
            self.error = str(exc)
        t = self.table_data
        self.i_name = t.index("Full Name")
        self.i_sent = t.index("Project Sent Date")
        self.i_received = t.index("Project Received Date")
        self.refresh()

    def set_mode(self, mode):
        self.mode = mode
        for b, m in self.filter_buttons:
            b.setChecked(m == mode)
        self.refresh()

    def refresh(self):
        t = self.table_data
        query = self.search.text()

        shown = []
        for i, row in enumerate(t.rows):
            sent = row[self.i_sent] if self.i_sent >= 0 else None
            received = row[self.i_received] if self.i_received >= 0 else None
            if self.mode == "sent" and sent is None:
                continue
            if self.mode == "received" and received is None:
                continue
            name = row[self.i_name] if self.i_name >= 0 else None
            if query.strip() and not filters.name_matches(query, name):
                continue
            shown.append(i)

        self.table.set_data(
            t.headers, [t.rows[i] for i in shown], indices=shown,
            chip_fn=self._chip, center=("Project Sent Date", "Project Received Date"))

        if self.error:
            set_status(self.status, "\u26A0  " + self.error.upper(), BAD)
        else:
            set_status(
                self.status,
                f"SHOWING {len(shown)} OF {len(t.rows)} INTERVIEWS   \u00B7   "
                f"CLICK A HEADER TO SORT   \u00B7   DOUBLE-CLICK A ROW FOR DETAILS")

    def _chip(self, header, value):
        """A missing date is a step that has not happened yet."""
        if value is None and header == "Project Sent Date":
            return ("NOT SENT", WARN)
        if value is None and header == "Project Received Date":
            return ("PENDING", WARN)
        return None

    def show_record(self, index):
        t = self.table_data
        if not 0 <= index < len(t.rows):
            return
        row = t.rows[index]
        name = row[self.i_name] if self.i_name >= 0 and row[self.i_name] else "Interview"
        RecordDialog("Interview record", str(name).title(), t.headers, row,
                     self.accent, self.window()).exec()
