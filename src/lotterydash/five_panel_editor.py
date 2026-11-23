"""Five independently editable Pick 3 panels for the project workspace."""
from decimal import Decimal

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QScrollArea, QMessageBox,
)
from .models import Pick3Play, PlayType, Draw


class PanelEditor(QGroupBox):
    def __init__(self, letter, changed, parent=None):
        super().__init__("Panel " + letter, parent)
        self.letter = letter
        self.changed = changed
        row = QGridLayout(self)
        self.enabled = QCheckBox("Use this panel")
        row.addWidget(self.enabled, 0, 0, 1, 2)
        self.digits = QLineEdit()
        self.digits.setPlaceholderText("000–999")
        self.digits.setMaxLength(3)
        self.digits.setMaximumWidth(120)
        row.addWidget(QLabel("Numbers"), 1, 0)
        row.addWidget(self.digits, 1, 1)
        self.play_type = QComboBox()
        for value in PlayType:
            self.play_type.addItem(value.value.replace("_", " ").title(), value.value)
        row.addWidget(QLabel("Play type"), 1, 2)
        row.addWidget(self.play_type, 1, 3)
        self.amount = QComboBox()
        for amount in ("1.00", "0.50"):
            self.amount.addItem("$" + amount, amount)
        row.addWidget(QLabel("Wager"), 2, 0)
        row.addWidget(self.amount, 2, 1)
        self.draw = QComboBox()
        for value in Draw:
            self.draw.addItem(value.value.title(), value.value)
        row.addWidget(QLabel("Draw time"), 2, 2)
        row.addWidget(self.draw, 2, 3)
        self.fireball = QCheckBox("Fireball")
        row.addWidget(self.fireball, 3, 0, 1, 2)
        reset = QPushButton("Clear panel " + letter)
        reset.clicked.connect(self.reset)
        row.addWidget(reset, 3, 2, 1, 2)
        self.digits.textChanged.connect(self._digits_changed)
        for signal in (
            self.enabled.toggled, self.fireball.toggled,
            self.play_type.currentIndexChanged, self.amount.currentIndexChanged,
            self.draw.currentIndexChanged,
        ):
            signal.connect(self.changed)

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
        layout.addWidget(QLabel("Pick 3 — Five-panel playslip editor"))
        layout.addWidget(QLabel(
            "Edit panels A–E independently. Check 'Use this panel' to include it. "
            "Save the project to retain changes."))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        inner = QVBoxLayout(content)
        self.panels = [PanelEditor(letter, self._changed) for letter in "ABCDE"]
        for panel in self.panels:
            inner.addWidget(panel)
        inner.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        footer = QHBoxLayout()
        self.summary = QLabel("0 / 5 panels")
        footer.addWidget(self.summary, 1)
        clear = QPushButton("Clear all panels")
        clear.clicked.connect(self.clear_all)
        footer.addWidget(clear)
        layout.addLayout(footer)
        self._changed()

    def _changed(self, *_):
        used = sum(p.enabled.isChecked() for p in self.panels)
        self.summary.setText(f"{used} / 5 panels selected")
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
        for panel in self.panels:
            try:
                play = panel.get_play()
            except ValueError as exc:
                raise ValueError(f"Panel {panel.letter}: {exc}") from exc
            if play is not None:
                plays.append(play)
        return plays
