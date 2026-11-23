"""Persistent, nested context explanations for LotteryDash controls."""
from html import escape
from PySide6.QtCore import QObject, QEvent, Qt, QSettings
from PySide6.QtWidgets import (
    QApplication, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextBrowser, QCheckBox, QPushButton, QComboBox, QTabBar, QToolButton,
    QAbstractButton, QLineEdit,
)
from .element_guide import ENTRIES

DEFINITIONS = {name.casefold(): (name, group, meaning) for name, group, meaning in ENTRIES}


class ContextInspector(QDockWidget):
    """A dock that remains visible while switching workspace tabs."""

    def __init__(self, parent):
        super().__init__("Context Help", parent)
        self.setObjectName("lotterydashContextInspector")
        self.settings = QSettings("LotteryDash", "LotteryDash")
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea |
                             Qt.DockWidgetArea.RightDockWidgetArea)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(5, 5, 5, 5)
        header = QHBoxLayout()
        self.pin = QCheckBox("Pin")
        self.pin.setToolTip("Keep the current explanation while navigating other controls.")
        header.addWidget(self.pin)
        header.addStretch()
        clear = QPushButton("Reset")
        clear.setToolTip("Unpin and return to the general context help introduction.")
        clear.clicked.connect(self.reset)
        header.addWidget(clear)
        layout.addLayout(header)
        self.path = QLabel("Workspace → Context Help")
        self.path.setWordWrap(True)
        self.path.setObjectName("mutedLabel")
        self._add_section(layout, "location", "Context location", self.path)
        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(False)
        self._add_section(layout, "explanation", "Explanation", self.detail, 1)
        self.setWidget(body)
        self._last = None
        self.pin.setChecked(self.settings.value("context_help/pinned", False, type=bool))
        self.pin.toggled.connect(lambda value: self.settings.setValue("context_help/pinned", value))
        self.reset(clear_pin=False)

    def _add_section(self, layout, key, title, widget, stretch=0):
        toggle = QToolButton(self)
        toggle.setText(title)
        toggle.setCheckable(True)
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setAutoRaise(True)
        expanded = self.settings.value(f"context_help/expanded/{key}", True, type=bool)
        toggle.setChecked(expanded)
        def changed(value):
            widget.setVisible(value)
            toggle.setArrowType(Qt.ArrowType.DownArrow if value else Qt.ArrowType.RightArrow)
            self.settings.setValue(f"context_help/expanded/{key}", value)
        toggle.toggled.connect(changed)
        changed(expanded)
        layout.addWidget(toggle)
        layout.addWidget(widget, stretch)

    def reset(self, clear_pin=True):
        if clear_pin:
            self.pin.setChecked(False)
        self._last = None
        self.path.setText("Workspace → Context Help")
        self.detail.setHtml(
            "<h3>Context Help</h3><p>Hover over or focus a control to see its meaning, "
            "current selection, and its place in the interface hierarchy.</p>"
            "<p>Use <b>Pin</b> to keep an explanation visible while you work.</p>")

    def show_context(self, path, title, meaning, value="", category=""):
        key = (path, title, meaning, value, category)
        if self.pin.isChecked() or key == self._last:
            return
        self._last = key
        self.path.setText(path)
        value_html = (
            f"<p><b>Current value:</b> {escape(value)}</p>" if value else "")
        group_html = f"<p><small>{escape(category)}</small></p>" if category else ""
        self.detail.setHtml(
            f"<h3>{escape(title)}</h3>{group_html}{value_html}"
            f"<p>{escape(meaning)}</p>")


class ContextTracker(QObject):
    def __init__(self, window, dock):
        super().__init__(window)
        self.window = window
        self.dock = dock

    def eventFilter(self, watched, event):
        if event.type() not in (QEvent.Type.Enter, QEvent.Type.FocusIn):
            return False
        if not isinstance(watched, QWidget) or not self.window.isAncestorOf(watched):
            return False
        if watched is self.dock or self.dock.isAncestorOf(watched):
            return False
        self.update_from_widget(watched)
        return False

    def update_from_widget(self, widget):
        # Follow ancestors so nested child widgets inherit the meaning of their
        # owning control. Never display internal Qt implementation class names.
        target = widget
        while target and target is not self.window:
            if isinstance(target, (QAbstractButton, QComboBox, QLineEdit, QTabBar)):
                break
            if target.toolTip():
                break
            target = target.parentWidget()
        if target is None or target is self.window:
            return
        title = ""
        value = ""
        if isinstance(target, QComboBox):
            title = target.accessibleName() or "Selection"
            value = target.currentText()
            item_tip = target.itemData(target.currentIndex(), Qt.ItemDataRole.ToolTipRole)
            tooltip = str(item_tip) if item_tip else target.toolTip()
        elif isinstance(target, QAbstractButton):
            title = target.text().replace("&", "").strip() or target.accessibleName() or "Option"
            if target.isCheckable():
                value = "Enabled" if target.isChecked() else "Disabled"
            tooltip = target.toolTip()
        elif isinstance(target, QLineEdit):
            title = target.accessibleName() or target.placeholderText() or "Input"
            value = target.text()
            tooltip = target.toolTip()
        elif isinstance(target, QTabBar):
            index = target.currentIndex()
            title = target.tabText(index) if index >= 0 else "Workspace tab"
            tooltip = target.tabToolTip(index) if index >= 0 else ""
        else:
            title = target.accessibleName() or target.objectName() or "Control"
            tooltip = target.toolTip()
        # Match glossary first, then explicit per-control explanation.
        definition = DEFINITIONS.get(title.casefold())
        if definition:
            _, category, meaning = definition
        else:
            category, meaning = "", tooltip or "This control belongs to the current workspace."
        # Selected play type is a nested definition under the panel's selector.
        if isinstance(target, QComboBox):
            selection = DEFINITIONS.get(value.casefold())
            if selection:
                _, category, meaning = selection
                title = f"{title}: {value}"
        panel = None
        for candidate in getattr(self.window.panel_editor, "panels", []):
            if target is candidate or candidate.isAncestorOf(target):
                panel = candidate
                break
        tab = self.window.tabs.tabText(self.window.tabs.currentIndex())
        path = f"Workspace → {tab}"
        if panel is not None:
            path += f" → Panel {panel.letter}"
            if isinstance(target, QComboBox):
                if target is panel.play_type:
                    title = f"Play type: {value}"
                elif target is panel.amount:
                    title = "Wager"
                elif target is panel.draw:
                    title = "Draw"
            elif target is panel.digits:
                title = "Numbers"
            elif target is panel.fireball:
                title = "Fireball"
            elif target is panel.enabled:
                title = "Use panel"
            path += f" → {title}"
        else:
            path += f" → {title}"
        self.dock.show_context(path, title, meaning, value, category)


def install_context_inspector(window):
    dock = ContextInspector(window)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    dock.setMinimumWidth(200)
    dock.resize(230, 450)
    settings = QSettings("LotteryDash", "LotteryDash")
    dock.setVisible(settings.value("context_help/visible", True, type=bool))
    dock.visibilityChanged.connect(
        lambda visible: settings.setValue("context_help/visible", visible))
    tracker = ContextTracker(window, dock)
    QApplication.instance().installEventFilter(tracker)
    window._context_tracker = tracker
    window.context_inspector = dock
    return dock
