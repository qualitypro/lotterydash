"""Contextual help for LotteryDash Qt controls.

Explicit tooltips always win. Unlabelled controls receive a conservative fallback
based on their actual visible label, tab text or input placeholder.
"""
from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import (
    QWidget, QAbstractButton, QComboBox, QLineEdit, QTabBar,
    QTabWidget, QLabel, QGroupBox, QSpinBox, QDoubleSpinBox,
    QSlider, QPlainTextEdit, QTextEdit, QAbstractItemView,
)

HELP = {
    "New": "Create a new project. The project is saved to your LotteryDash projects folder.",
    "Open": "Choose an existing saved LotteryDash project.",
    "Save": "Save the current project and its panel selections.",
    "Save As": "Save a copy of the current project under another filename.",
    "Game": "Choose the lottery game for this project. Pick 3 has an editable five-panel playslip; other games may have limited editing support.",
    "Play": "Set up to five Pick 3 plays. Each row specifies digits, how to match them, wager, draw and optional Fireball.",
    "Playslip": "Inspect which bubbles would be selected on the scanned playslip. This is a visual check, not proof of printer calibration.",
    "Mapping Studio": "Choose a scan and edit bubble positions. Review mappings before publication.",
    "Print / Proof": "Generate PDF proofs. A proof is not confirmation of printer alignment.",
    "Settings": "View project metadata and asset references.",
    "Choose scan": "Choose the image of the physical playslip used for mapping.",
    "Choose mapping draft": "Select a draft JSON mapping containing playslip bubble coordinates.",
    "Edit mapping": "Launch the mapping editor for the project's scan and draft mapping.",
    "Publish reviewed mapping": "Publish a versioned mapping snapshot after review. Does not calibrate a printer.",
    "Preview mapped selections": "Show where the current plays are marked on the selected playslip mapping.",
    "Export draft PDF": "Create a planning PDF, not a printer-calibrated playslip.",
    "Export mapped PDF proof": "Create a scan-aligned visual proof; verify printer alignment separately.",
    "Clear all": "Reset all five panels. Save the project afterward to retain the change.",
    "Clear": "Reset this panel only.",
    "Pick 3  /  Playslip": "Each row represents a physical Pick 3 panel, A through E. Choose numbers, play type, wager, draw and Fireball.",
    "0 of 5 panels": "Shows how many of the five possible Pick 3 panels are currently enabled.",
}


def _fallback(widget):
    if isinstance(widget, QTabBar):
        return None
    if isinstance(widget, QAbstractButton):
        label = widget.text().replace("&", "").strip()
        if label:
            return HELP.get(label, f"{label}: activate this action.")
    if isinstance(widget, QComboBox):
        return widget.accessibleDescription() or (
            "Choose an option from this list. Your selection applies to this field.")
    if isinstance(widget, QLineEdit):
        placeholder = widget.placeholderText()
        return (f"Enter {placeholder}." if placeholder else
                "Enter or edit the value in this field.")
    if isinstance(widget, (QSpinBox, QDoubleSpinBox, QSlider)):
        return "Adjust this numeric setting."
    if isinstance(widget, (QPlainTextEdit, QTextEdit)):
        return "Enter or edit the text in this field."
    if isinstance(widget, QGroupBox) and widget.title():
        return widget.title() + ": controls grouped for this setting."
    if isinstance(widget, QLabel) and widget.text().strip():
        label = widget.text().strip()
        return HELP.get(label)
    if isinstance(widget, QAbstractItemView):
        return "Select an item to inspect or edit it."
    return None


class HelpTooltips(QObject):
    """Provide missing tooltips, including controls in dialogs created later."""

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.ToolTip and isinstance(watched, QWidget):
            if not watched.toolTip():
                message = _fallback(watched)
                if message:
                    watched.setToolTip(message)
        return False


def install_help(app):
    filter_instance = HelpTooltips(app)
    app.installEventFilter(filter_instance)
    return filter_instance
