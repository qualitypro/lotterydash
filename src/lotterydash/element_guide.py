"""Searchable in-application guide to lottery terms and LotteryDash controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QLabel, QTextBrowser, QComboBox, QSplitter,
)

ENTRIES = [
    ("Pick 3", "Game rules", "Choose three digits, 000–999. A drawing produces three digits in order. How you win depends on the selected play type."),
    ("Panel A–E", "Playslip", "Five separate positions on a physical playslip. Each configured panel has its own numbers, play type, wager, draw and optional Fireball."),
    ("Numbers", "Playslip", "Enter exactly three digits, including leading zeros such as 007. These are the numbers you want to play."),
    ("Straight", "Play types", "All three digits must match the drawn digits in the exact same order. For 123, only 123 is an exact-order match."),
    ("Box", "Play types", "Match all three selected digits in any order. Three distinct digits have six arrangements; two identical digits give three. Three identical digits are not a standard Box play."),
    ("Straight/Box", "Play types", "Combines Straight and Box play types. The selected amount is divided between the components; consult the official prize table for details."),
    ("Combo", "Play types", "Covers each distinct order as a separate Straight combination. The number of combinations depends on repeated digits, and the total wager can exceed the displayed base wager."),
    ("Front Pair", "Play types", "The first two digits must match the first two drawn digits in the correct order."),
    ("Back Pair", "Play types", "The last two digits must match the last two drawn digits in the correct order."),
    ("Wager", "Game rules", "Money staked on a selection. The final ticket cost may be affected by Combo and optional Fireball selections. This application is not a purchase system."),
    ("Midday", "Game rules", "The daytime drawing. Confirm the ticket's date and purchase cutoff with the official lottery."),
    ("Evening", "Game rules", "The later drawing. Confirm the ticket's date and purchase cutoff with the official lottery."),
    ("Fireball", "Game rules", "Optional add-on with an additional wager. A separate Fireball digit is drawn and may substitute for one regular drawn digit to create additional winning combinations. Prize rules differ from the base play."),
    ("Use panel", "Playslip", "Checking a panel includes its selection in the saved playslip and preview. Entering digits also enables the panel automatically."),
    ("Clear panel", "Playslip", "Resets only one panel's numbers and selections. Save the project to retain the reset."),
    ("Clear all", "Playslip", "Resets all five panels. Save afterward if you want the cleared configuration persisted."),
    ("Completion graph", "Playslip", "Counts enabled panels out of five. It does not certify valid selections or printing accuracy."),
    ("Visual Play Guide", "Playslip", "Displays examples for the focused panel, including Straight and Box number arrangements. Examples are educational, not payout estimates."),
    ("Project", "Projects", "A saved configuration containing a game, play selections and references to the selected scan and mapping."),
    ("New", "Projects", "Creates and saves a new project file."),
    ("Open", "Projects", "Opens a previously saved LotteryDash project."),
    ("Save", "Projects", "Writes the current project configuration and plays to its existing file."),
    ("Save As", "Projects", "Writes the project to another file location or name."),
    ("Scan", "Mapping", "An image of the physical lottery playslip used as the reference for bubble positions."),
    ("Mapping draft", "Mapping", "A working set of field coordinates identifying where bubbles appear on the scanned playslip."),
    ("Mapping Studio", "Mapping", "Workspace for selecting scans, editing mappings and publishing reviewed versions."),
    ("Publish mapping", "Mapping", "Creates a versioned snapshot of a reviewed mapping. This does not verify printer calibration."),
    ("Mapped preview", "Mapping", "Visualizes selected bubbles against the scanned slip. It does not prove printed alignment."),
    ("Draft PDF", "Printing", "Planning document for reviewing plays, not an official printed playslip."),
    ("Mapped PDF proof", "Printing", "A visual PDF proof aligned to the current scan and mapping; printer calibration remains necessary."),
    ("Printer calibration", "Printing", "Verification that the physical printer places marks correctly on the actual slip at the intended paper size and feed orientation."),
]

CATEGORIES = ["All topics", "Game rules", "Play types", "Playslip", "Projects", "Mapping", "Printing"]


class ElementGuide(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        header = QLabel("Element Guide")
        header.setObjectName("sectionTitle")
        header.setToolTip("Reference library explaining LotteryDash interface elements and Pick 3 terms.")
        outer.addWidget(header)
        description = QLabel("Search a control, game term, or workflow. Select an entry to read its meaning.")
        description.setWordWrap(True)
        outer.addWidget(description)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search meanings, e.g. Fireball, Box, mapping...")
        self.search.setClearButtonEnabled(True)
        self.search.setToolTip("Filter the guide by term or explanation. Search is not case-sensitive.")
        filters.addWidget(self.search, 1)
        self.category = QComboBox()
        self.category.addItems(CATEGORIES)
        self.category.setToolTip("Filter guide entries by game rules, play types or application feature.")
        filters.addWidget(self.category)
        outer.addLayout(filters)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.items = QListWidget()
        self.items.setToolTip("Choose an element to read its full explanation.")
        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(False)
        self.detail.setToolTip("Explanation of the selected element and how it is used.")
        splitter.addWidget(self.items)
        splitter.addWidget(self.detail)
        splitter.setSizes([240, 650])
        outer.addWidget(splitter, 1)
        self.search.textChanged.connect(self.refresh)
        self.category.currentIndexChanged.connect(self.refresh)
        self.items.currentRowChanged.connect(self.show_selection)
        self._visible = []
        self.refresh()

    def refresh(self, *_):
        term = self.search.text().strip().casefold()
        category = self.category.currentText()
        self._visible = [
            entry for entry in ENTRIES
            if (category == "All topics" or entry[1] == category)
            and (not term or term in " ".join(entry).casefold())
        ]
        self.items.blockSignals(True)
        self.items.clear()
        for title, group, _ in self._visible:
            self.items.addItem(title)
        self.items.blockSignals(False)
        if self._visible:
            self.items.setCurrentRow(0)
            self.show_selection(0)
        else:
            self.detail.setPlainText("No matching elements. Try another search term or category.")

    def show_selection(self, index):
        if 0 <= index < len(self._visible):
            title, category, meaning = self._visible[index]
            from html import escape
            self.detail.setHtml(
                f"<h2>{escape(title)}</h2><p><b>{escape(category)}</b></p>"
                f"<p>{escape(meaning)}</p>"
                "<p><small>For official rules, ticket pricing and prizes, consult the Florida Lottery.</small></p>"
            )
