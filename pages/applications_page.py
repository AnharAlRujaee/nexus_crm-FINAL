"""Page 4 - Applications (data from data/Applications.xlsx)."""

from PyQt6.QtWidgets import QHBoxLayout

from core import filters
from core.data_store import DataError, Table, load_applications
from ui.base_page import BasePage
from ui.data_table import RecordDialog, build_table_panel, set_status
from ui.theme import ACCENTS, BAD, OK, TEXT_DIM, WARN
from ui.widgets import (
    GlassPanel, NeonButton, NeonComboBox, NeonLineEdit, PageHeader, StatusChip, make_label,
)

CENTERED = (
    "Application Period", "English Level", "Dutch Level", "Green Check",
    "Internal Tracking 1", "Internal Tracking 2", "Internal Tracking 3",
)

class ApplicationsPage(BasePage):
    VIEWS = [
        "All records", 
        "Duplicates only", 
        "Unique (duplicates removed)",
        "Previous VIT Check (In VIT1/VIT2)",
        "Different Record (Not in VIT1/VIT2)"
    ]

    def __init__(self, nav):
        super().__init__(nav, ACCENTS["applications"], "applications", "APPLICATIONS")
        self.mode = "all"
        self.table_data = Table([], [])
        self.error = ""
        self.dup_flags, self.first_flags = [], []
        self.i_name = self.i_email = self.i_mentor = -1
        self.i_vit1 = self.i_vit2 = -1

        header = PageHeader(
            "apps", "Module 01", "Application pipeline",
            "Search, filter and review every application record.", self.accent)
        header.add_chip(StatusChip("GOOGLE DRIVE SYNC", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        # search + record view
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
        sl.addSpacing(10)
        sl.addWidget(make_label("RECORDS", 11, TEXT_DIM, True, 2.2, mono=True))
        
        self.view = NeonComboBox(self.accent)
        self.view.addItems(self.VIEWS)
        self.view.setMinimumWidth(330)
        self.view.currentIndexChanged.connect(lambda _i: self.refresh())
        sl.addWidget(self.view)
        
        self.root.addWidget(search_panel)
        self.reveal(search_panel)

        # mentor-meeting filters
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
        panel, self.table, self.status = build_table_panel(self.accent)
        self.table.record_activated.connect(self.show_record)
        self.root.addWidget(panel, 1)
        self.reveal(panel)

        self.add_row([self.back_button()], stretch_end=True)

    def on_enter(self):
        self.reload()
        super().on_enter()

    def reload(self):
        try:
            self.table_data = load_applications()
            self.error = ""
        except DataError as exc:
            self.table_data = Table([], [])
            self.error = str(exc)
            
        t = self.table_data
        self.i_name = t.index("Full Name")
        self.i_email = t.index("Email")
        self.i_mentor = t.index("Mentor Meeting")
        
        self.i_vit1 = t.index("VIT1") if t.index("VIT1") >= 0 else t.index("VIT 1")
        self.i_vit2 = t.index("VIT2") if t.index("VIT2") >= 0 else t.index("VIT 2")

        if hasattr(filters, "duplicate_flags"):
            self.dup_flags, self.first_flags = filters.duplicate_flags(t.rows, self.i_name, self.i_email)
        else:
            self.dup_flags = [False] * len(t.rows)
            self.first_flags = [True] * len(t.rows)

        self.refresh()

    def set_mode(self, mode):
        self.mode = mode
        for b, m in self.filter_buttons:
            b.setChecked(m == mode)
        self.refresh()

    def _has_meeting(self, row):
        value = row[self.i_mentor] if self.i_mentor >= 0 else None
        return value is not None and str(value).strip().upper() == "OK"
        
    def _is_in_vit(self, row):
        in_vit1 = in_vit2 = False
        if self.i_vit1 >= 0:
            val1 = row[self.i_vit1]
            in_vit1 = val1 is not None and str(val1).strip() != ""
        if self.i_vit2 >= 0:
            val2 = row[self.i_vit2]
            in_vit2 = val2 is not None and str(val2).strip() != ""
        return in_vit1 or in_vit2

    def refresh(self):
        t = self.table_data
        query = self.search.text()
        view = self.view.currentIndex()

        shown = []
        for i, row in enumerate(t.rows):
            if self.mode == "defined" and not self._has_meeting(row):
                continue
            if self.mode == "not_defined" and self._has_meeting(row):
                continue
                
            if view == 1 and not self.dup_flags[i]: 
                continue
            if view == 2 and not self.first_flags[i]:
                continue
            if view == 3 and not self._is_in_vit(row):
                continue
            if view == 4 and self._is_in_vit(row):
                continue
                
            name = row[self.i_name] if self.i_name >= 0 else None
            if hasattr(filters, "name_matches"):
                if query.strip() and not filters.name_matches(query, name):
                    continue
            else:
                if query.strip() and query.casefold() not in str(name).casefold():
                    continue
                    
            shown.append(i)

        self.table.set_data(
            t.headers, [t.rows[i] for i in shown], indices=shown,
            chip_fn=self._chip, center=CENTERED)

        if self.error:
            set_status(self.status, "\u26A0  " + self.error.upper(), BAD)
        else:
            dups = sum(1 for flag in self.dup_flags if flag)
            set_status(
                self.status,
                f"SHOWING {len(shown)} OF {len(t.rows)} APPLICATIONS   \u00B7   "
                f"{dups} DUPLICATE ROWS   \u00B7   CLICK A HEADER TO SORT   \u00B7   "
                f"DOUBLE-CLICK A ROW FOR FULL DETAILS")

    def _chip(self, header, value):
        if value is None:
            return None
        text = str(value).strip().upper()
        if header == "Mentor Meeting":
            return (text, OK if text == "OK" else WARN)
        if header == "Processing Status":
            return (text, OK if text == "DONE" else WARN)
        if header == "Application Period":
            return (text, self.accent)
        return None

    def show_record(self, index):
        t = self.table_data
        if not 0 <= index < len(t.rows):
            return
        row = t.rows[index]
        name = row[self.i_name] if self.i_name >= 0 and row[self.i_name] else "Application"
        RecordDialog("Application record", str(name).title(), t.headers, row,
                     self.accent, self.window()).exec()