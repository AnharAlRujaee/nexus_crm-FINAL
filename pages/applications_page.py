"""Page 4 - Applications (loaded from data/Applications.xlsx)."""

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout

from data_service import (
    application_duplicates, load_applications, load_interviews, load_mentor,
    meeting_identified, previous_vit_rows, unique_applications, different_record_rows,
)
from ui.base_page import BasePage
from ui.theme import ACCENTS, TEXT_DIM
from ui.widgets import (
    DataTable, GlassPanel, NeonButton, NeonComboBox, NeonLineEdit, PageHeader, StatusChip,
    make_label,
)


class ApplicationsPage(BasePage):
    MORE_VIEWS = [
        ("Choose extra view…", None),
        ("Duplicate records", "duplicates"),
        ("Previous VIT check", "previous_vit"),
        ("Different records", "different"),
        ("Unique applications", "unique"),
    ]

    def __init__(self, nav):
        super().__init__(nav, ACCENTS["applications"], "applications", "APPLICATIONS")
        self.mode = "all"
        self.table_data = None

        header = PageHeader(
            "apps", "Module 01", "Application pipeline",
            "Search, filter and review every column from Applications.xlsx.", self.accent)
        header.add_chip(StatusChip("LIVE DATA", self.accent))
        self.root.addWidget(header)
        self.reveal(header)

        search_panel = GlassPanel(self.accent, radius=16)
        sl = QHBoxLayout(search_panel)
        sl.setContentsMargins(14, 6, 14, 6)
        sl.setSpacing(8)
        self.search = NeonLineEdit("Search by name or surname prefix (e.g. As)…", "search", self.accent)
        sl.addWidget(self.search, 1)
        search_btn = NeonButton("Search", self.accent, icon="search")
        search_btn.clicked.connect(self.refresh)
        self.search.returnPressed.connect(self.refresh)
        sl.addWidget(search_btn)
        self.root.addWidget(search_panel)
        self.reveal(search_panel)

        self.filter_buttons = []
        for text, mode, icon in (
            ("All Applications", "all", "list"),
            ("Mentor Meeting Identified", "defined", "check"),
            ("Mentor Meeting Not Identified", "not_defined", "cross"),
        ):
            b = NeonButton(text, self.accent, icon=icon, variant="ghost", height=42)
            b.setCheckable(True)
            b.clicked.connect(lambda _checked=False, m=mode: self.set_mode(m))
            self.filter_buttons.append((b, mode))
        self.filter_buttons[0][0].setChecked(True)
        self.add_row([b for b, _ in self.filter_buttons], stretch_end=True)

        extra = GlassPanel(self.accent, radius=16)
        el = QHBoxLayout(extra)
        el.setContentsMargins(14, 6, 18, 6)
        el.setSpacing(12)
        el.addWidget(make_label("MORE VIEWS", 11, TEXT_DIM, True, 2.2, mono=True))
        self.more = NeonComboBox(self.accent)
        self.more.addItems([label for label, _ in self.MORE_VIEWS])
        self.more.currentIndexChanged.connect(self._on_more)
        el.addWidget(self.more, 1)
        self.root.addWidget(extra)
        self.reveal(extra)

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
            self.table_data = load_applications()
            self._mentor = load_mentor()
            self._interviews = load_interviews()
        except Exception as exc:
            self.table_data = None
            self.table.load(["Error"], [[str(exc)]])
            self.count.setText("COULD NOT LOAD APPLICATIONS.XLSX")
            return
        self.refresh()

    def set_mode(self, mode):
        self.mode = mode
        for b, m in self.filter_buttons:
            b.setChecked(m == mode)
        self.more.blockSignals(True)
        self.more.setCurrentIndex(0)
        self.more.blockSignals(False)
        self.refresh()

    def _on_more(self, index):
        mode = self.MORE_VIEWS[index][1]
        if mode is None:
            return
        self.mode = mode
        for b, _m in self.filter_buttons:
            b.setChecked(False)
        self.refresh()

    def refresh(self):
        if self.table_data is None:
            return
        source = self.table_data
        headers, rows = source.headers, list(source.rows)
        meet_i = source.col("Mentor Meeting")

        if self.mode == "defined":
            rows = [r for r in rows if meeting_identified(r[meet_i])]
        elif self.mode == "not_defined":
            rows = [r for r in rows if not meeting_identified(r[meet_i])]
        elif self.mode == "duplicates":
            rows = application_duplicates(source)
        elif self.mode == "previous_vit":
            rows = previous_vit_rows(source, self._mentor, self._interviews)
        elif self.mode == "different":
            headers, rows = different_record_rows(self._mentor, self._interviews)
        elif self.mode == "unique":
            rows = unique_applications(source)

        query = self.search.text()
        if query.strip() and headers:
            name_key = "Full Name" if "Full Name" in headers else headers[0]
            i = headers.index(name_key)
            from data_service import name_matches
            rows = [r for r in rows if name_matches(r[i], query)]

        self.table.load(headers, rows, self.accent)
        total = len(source.rows)
        self.count.setText(f"SHOWING {len(rows)} ROW{'S' if len(rows) != 1 else ''}  ·  {total} IN APPLICATIONS.XLSX")
