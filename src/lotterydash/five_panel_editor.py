"""Compact, independently editable five-row Pick 3 playslip editor."""
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QFrame, QHeaderView,
    QSizePolicy,
)
from .models import Pick3Play, PlayType, Draw


PLAY_HELP = {
    "straight": "STRAIGHT: Your three digits must match the drawn digits in the same order. Example: 123 wins only on 123.",
    "box": "BOX: Your digits can match in any order. Three distinct digits have 6 possible orders; one repeated digit gives 3. All three equal digits do not make a standard Box play.",
    "straight_box": "STRAIGHT/BOX: Combines an exact-order Straight play with a Box play. The selected wager is divided between the two components.",
    "combo": "COMBO: Covers each distinct arrangement of the three selected digits as a separate Straight combination. Cost depends on the number of combinations; verify the total before purchasing.",
    "front_pair": "FRONT PAIR: The first two selected digits must match the first two drawn digits in exact order. The third digit does not determine this pair win.",
    "back_pair": "BACK PAIR: The last two selected digits must match the last two drawn digits in exact order. The first digit does not determine this pair win.",
}

class PanelEditor(QWidget):
    """One playslip row. Attribute names retained for project integration."""

    def __init__(self, letter, changed, parent=None):
        super().__init__(parent)
        self.letter = letter
        self.changed = changed
        row = QHBoxLayout(self)
        row.setContentsMargins(7, 5, 7, 5)
        row.setSpacing(8)
        self.enabled = QCheckBox(letter)
        self.enabled.setToolTip("Include panel " + letter + " in the saved playslip and PDF proof.")
        self.enabled.setFixedWidth(47)
        row.addWidget(self.enabled)
        self.digits = QLineEdit()
        self.digits.setPlaceholderText("000")
        self.digits.setToolTip("Enter exactly three digits (000–999). Leading zeros are valid.")
        self.digits.setMaxLength(3)
        self.digits.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]{0,3}")))
        self.digits.setFixedWidth(86)
        self.digits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.digits)
        self.play_type = QComboBox()
        for value in PlayType:
            self.play_type.addItem(value.value.replace("_", " ").title(), value.value)
        for i in range(self.play_type.count()):
            code = self.play_type.itemData(i)
            self.play_type.setItemData(i, PLAY_HELP.get(code, ""), Qt.ItemDataRole.ToolTipRole)
        self.play_type.currentIndexChanged.connect(self._update_play_help)
        self._update_play_help()
        self.play_type.setMinimumWidth(150)
        row.addWidget(self.play_type, 2)
        self.amount = QComboBox()
        for amount in ("1.00", "0.50"):
            self.amount.addItem("$" + amount, amount)
        self.amount.setToolTip(
            "Choose a $0.50 or $1.00 base wager. Straight/Box splits its wager; "
            "Combo and Fireball may change the total cost. Do not assume this value is the ticket total.")
        self.amount.setFixedWidth(88)
        row.addWidget(self.amount)
        self.draw = QComboBox()
        for value in Draw:
            self.draw.addItem(value.value.title(), value.value)
        self.draw.setToolTip(
            "Midday selects the daytime Pick 3 drawing; Evening selects the later drawing. "
            "Check ticket dates and retailer cut-off times.")
        self.draw.setFixedWidth(110)
        self.draw.setCurrentIndex(1)
        row.addWidget(self.draw)
        self.fireball = QCheckBox()
        self.fireball.setToolTip(
            "FIREBALL: An optional extra wager. A separate digit is drawn and can replace "
            "one digit in the regular Pick 3 result to form additional winning combinations. "
            "Fireball has its own prize rules and additional cost.")
        self.fireball.setFixedWidth(56)
        row.addWidget(self.fireball, alignment=Qt.AlignmentFlag.AlignCenter)
        reset = QPushButton("Clear")
        reset.setObjectName("subtleButton")
        reset.setFixedWidth(64)
        reset.setToolTip("Clear panel " + letter)
        reset.clicked.connect(self.reset)
        row.addWidget(reset)
        self.digits.textChanged.connect(self._digits_changed)
        for signal in (
            self.enabled.toggled, self.fireball.toggled,
            self.play_type.currentIndexChanged, self.amount.currentIndexChanged,
            self.draw.currentIndexChanged,
        ):
            signal.connect(self.changed)

    def _update_play_help(self, *_):
        self.play_type.setToolTip(PLAY_HELP.get(self.play_type.currentData(), "Select the play type."))

    def _digits_changed(self, text):
        if text and not self.enabled.isChecked():
            self.enabled.setChecked(True)
        self.changed()

    def reset(self):
        self.enabled.setChecked(False)
        self.digits.clear()
        self.play_type.setCurrentIndex(0)
        self.amount.setCurrentIndex(0)
        self.draw.setCurrentIndex(1)
        self.fireball.setChecked(False)
        self.changed()

    def load_play(self, play):
        self.digits.setText(play.digits)
        self.play_type.setCurrentIndex(self.play_type.findData(play.play_type.value))
        self.amount.setCurrentIndex(self.amount.findData(str(play.amount)))
        self.draw.setCurrentIndex(self.draw.findData(play.draw.value))
        self.fireball.setChecked(play.fireball)
        self.enabled.setChecked(True)

    def get_play(self):
        if not self.enabled.isChecked():
            return None
        return Pick3Play(
            digits=self.digits.text(), play_type=self.play_type.currentData(),
            amount=Decimal(self.amount.currentData()), draw=self.draw.currentData(),
            fireball=self.fireball.isChecked(),
        )


class FivePanelEditor(QWidget):
    def __init__(self, on_change=None, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        title = QLabel("Pick 3  /  Playslip")
        title.setObjectName("sectionTitle")
        heading.addWidget(title)
        heading.addStretch()
        self.summary = QLabel("0 of 5 panels")
        self.summary.setObjectName("mutedLabel")
        heading.addWidget(self.summary)
        layout.addLayout(heading)

        sheet = QFrame()
        sheet.setObjectName("panelSheet")
        grid = QVBoxLayout(sheet)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(0)
        headers = QWidget()
        labels = QHBoxLayout(headers)
        labels.setContentsMargins(7, 0, 7, 5)
        labels.setSpacing(8)
        explanations = {
            "Panel": "Panels A–E correspond to the five play positions on the physical playslip. Check a letter to include it.",
            "Numbers": "Three digits for the selected panel, including leading zeros such as 007.",
            "Play type": "Straight requires exact order; Box allows any order; Straight/Box combines both; Combo covers arrangements; Front/Back Pair use two digits. Hover over the selector for the chosen type.",
            "Wager": "Choose a $0.50 or $1.00 base wager. Combo and Fireball can increase total ticket cost.",
            "Draw": "Midday or Evening Pick 3 drawing. Verify the ticket date and purchase cut-off.",
            "Fireball": "Optional separately drawn digit that can replace one digit in the Pick 3 result. Adds cost and extra ways to win.",
        }
        for title, width, stretch in (
            ("Panel", 47, 0), ("Numbers", 86, 0), ("Play type", 150, 2),
            ("Wager", 88, 0), ("Draw", 110, 0), ("Fireball", 56, 0),
            ("", 64, 0),
        ):
            label = QLabel(title)
            label.setObjectName("columnHeader")
            label.setToolTip(explanations.get(title, "Panel action"))
            if width:
                label.setMinimumWidth(width)
                if stretch == 0:
                    label.setMaximumWidth(width)
            labels.addWidget(label, stretch)
        grid.addWidget(headers)
        self.panels = [PanelEditor(letter, self._changed) for letter in "ABCDE"]
        for index, panel in enumerate(self.panels):
            panel.setObjectName("panelRowEven" if index % 2 == 0 else "panelRowOdd")
            grid.addWidget(panel)
        layout.addWidget(sheet)
        footer = QHBoxLayout()
        hint = QLabel("Enter three digits per row; filled rows are enabled automatically.")
        hint.setObjectName("mutedLabel")
        footer.addWidget(hint, 1)
        clear = QPushButton("Clear all")
        clear.setObjectName("subtleButton")
        clear.clicked.connect(self.clear_all)
        footer.addWidget(clear)
        layout.addLayout(footer)
        layout.addStretch()
        self._changed()

    def _changed(self, *_):
        used = sum(p.enabled.isChecked() for p in self.panels)
        self.summary.setText(f"{used} of 5 panels")
        if self.on_change:
            self.on_change()

    def clear_all(self):
        for panel in self.panels:
            panel.reset()

    def set_plays(self, plays):
        if len(plays) > 5:
            raise ValueError("Maximum five panels")
        self.clear_all()
        for panel, play in zip(self.panels, plays):
            panel.load_play(play)
        self._changed()

    def collect_plays(self):
        plays = []
        gap = False
        for panel in self.panels:
            if not panel.enabled.isChecked():
                gap = True
                continue
            if gap:
                raise ValueError(
                    "Panels must be filled consecutively from A to E.")
            try:
                play = panel.get_play()
            except ValueError as exc:
                raise ValueError(f"Panel {panel.letter}: {exc}") from exc
            if play is not None:
                plays.append(play)
        return plays
