"""Guided, non-printing game project setup for every catalog game."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLabel, QComboBox,
    QLineEdit, QCheckBox, QTextEdit, QGroupBox,
)
from .projects import GAMES, GAME_GROUPS, IMPLEMENTED_EDITORS

DEFAULTS = {
    "pick2": {"draw": "evening", "wager": "1.00"},
    "pick3": {"draw": "evening", "wager": "1.00", "fireball": False},
    "pick4": {"draw": "evening", "wager": "1.00", "fireball": False},
    "pick5": {"draw": "evening"},
    "fantasy5": {"draw": "evening"},
    "cashpop": {"draw": "evening"},
    "floridalotto": {},
    "jackpottripleplay": {},
    "powerball": {},
    "megamillions": {},
}
PICK_GAMES = frozenset(("pick2", "pick3", "pick4"))
DAILY_GAMES = frozenset(("pick2", "pick3", "pick4", "pick5", "fantasy5", "cashpop"))


def validate_setup(game, options):
    if game not in GAMES:
        raise ValueError("Unsupported game")
    if not isinstance(options, dict):
        raise ValueError("Game options must be an object")
    allowed = set(DEFAULTS[game])
    if set(options) - allowed:
        raise ValueError("Unsupported game options")
    if "draw" in options and options["draw"] not in ("midday", "evening"):
        raise ValueError("Invalid draw selection")
    if "wager" in options and options["wager"] not in ("0.50", "1.00"):
        raise ValueError("Invalid base wager")
    if "fireball" in options and not isinstance(options["fireball"], bool):
        raise ValueError("Fireball must be enabled or disabled")
    return dict(options)


class GameSetupWizard(QWizard):
    """Compact project wizard; setup does not enable unsupported editors or printing."""

    def __init__(self, parent=None, project=None, initial_game="pick3"):
        super().__init__(parent)
        self.editing = project is not None
        self.existing = project or {}
        self.setWindowTitle("Edit Game Setup" if self.editing else "New Game Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(510, 400)

        first = QWizardPage()
        first.setTitle("Choose a game")
        first.setSubTitle("Create a project for any supported Florida draw game.")
        form = QFormLayout(first)
        self.name = QLineEdit(self.existing.get("name", ""))
        self.name.setMaxLength(120)
        self.name.setPlaceholderText("e.g. Friday plays")
        first.registerField("projectName*", self.name)
        form.addRow("Project name", self.name)
        self.game = QComboBox()
        for group, codes in GAME_GROUPS.items():
            for code in codes:
                self.game.addItem(GAMES[code], code)
                self.game.setItemData(self.game.count() - 1, group, 3)
        selected = self.existing.get("game", initial_game)
        index = self.game.findData(selected)
        self.game.setCurrentIndex(max(index, 0))
        self.game.setEnabled(not self.editing)
        form.addRow("Game", self.game)
        self.capability = QLabel()
        self.capability.setWordWrap(True)
        form.addRow("", self.capability)
        self.addPage(first)

        second = QWizardPage()
        second.setTitle("Game preferences")
        second.setSubTitle("Defaults can be reviewed later; no ticket is purchased or printed.")
        options = QFormLayout(second)
        self.draw = QComboBox()
        self.draw.addItem("Evening", "evening")
        self.draw.addItem("Midday", "midday")
        options.addRow("Preferred draw", self.draw)
        self.wager = QComboBox()
        self.wager.addItem("$1.00", "1.00")
        self.wager.addItem("$0.50", "0.50")
        options.addRow("Base wager", self.wager)
        self.fireball = QCheckBox("Use Fireball by default")
        options.addRow("Fireball", self.fireball)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Optional project notes")
        self.notes.setMaximumHeight(75)
        options.addRow("Notes", self.notes)
        self.addPage(second)

        third = QWizardPage()
        third.setTitle("Review setup")
        third.setSubTitle("Finish saves the configuration. Printing still requires a supported workflow and calibration.")
        review_layout = QVBoxLayout(third)
        self.review = QLabel()
        self.review.setWordWrap(True)
        review_layout.addWidget(self.review)
        review_layout.addStretch()
        self.addPage(third)

        config = self.existing.get("game_setup", {})
        if not isinstance(config, dict):
            config = {}
        config = {**DEFAULTS.get(selected, {}), **config}
        self.draw.setCurrentIndex(max(0, self.draw.findData(config.get("draw", "evening"))))
        self.wager.setCurrentIndex(max(0, self.wager.findData(config.get("wager", "1.00"))))
        self.fireball.setChecked(config.get("fireball", False) is True)
        self.notes.setPlainText(str(self.existing.get("notes", "")))
        self.game.currentIndexChanged.connect(self._refresh)
        self.currentIdChanged.connect(self._refresh)
        self.name.textChanged.connect(self._refresh)
        self.draw.currentIndexChanged.connect(self._refresh)
        self.wager.currentIndexChanged.connect(self._refresh)
        self.fireball.toggled.connect(self._refresh)
        self._refresh()

    def _refresh(self, *_):
        game = self.game.currentData()
        self.draw.setEnabled(game in DAILY_GAMES)
        self.wager.setEnabled(game in PICK_GAMES)
        self.fireball.setEnabled(game in ("pick3", "pick4"))
        ready = game in IMPLEMENTED_EDITORS
        self.capability.setText(
            "Pick 3 editor and draft proof workflow available; printer calibration is separate."
            if ready else
            "Project configuration only. A game-specific editor, mapping and printing workflow are not yet implemented."
        )
        setup = self.setup_options()
        fields = "\n".join(f"  {key.replace('_', ' ').title()}: {value}" for key, value in setup.items())
        self.review.setText(
            f"Project: {self.name.text().strip() or '(enter a name)'}\n"
            f"Game: {GAMES[game]}\n"
            + (f"Preferences:\n{fields}\n" if fields else "No game-specific preferences.\n")
            + ("Editor: available (Pick 3)\n" if ready else "Editor: not yet available\n")
            + "No printing or purchase will occur."
        )

    def setup_options(self):
        game = self.game.currentData()
        result = {}
        if game in DAILY_GAMES:
            result["draw"] = self.draw.currentData()
        if game in PICK_GAMES:
            result["wager"] = self.wager.currentData()
        if game in ("pick3", "pick4"):
            result["fireball"] = self.fireball.isChecked()
        return validate_setup(game, result)

    def project_details(self):
        return {
            "name": self.name.text().strip(),
            "game": self.game.currentData(),
            "game_setup": self.setup_options(),
            "notes": self.notes.toPlainText().strip(),
        }
