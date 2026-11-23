"""Context help glossary lookup and dock smoke tests."""
import pytest
pytest.importorskip("PySide6")
from lotterydash.context_inspector import DEFINITIONS, ContextInspector


def test_nested_play_definitions():
    assert "box" in DEFINITIONS
    assert "fireball" in DEFINITIONS
    assert "mapping draft" in DEFINITIONS


def test_dock_pin_and_reset():
    from PySide6.QtWidgets import QMainWindow
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    dock = ContextInspector(window)
    dock.show_context("Workspace → Play → Panel A", "Box", "Match any order", "Box")
    assert "Box" in dock.detail.toPlainText()
    dock.pin.setChecked(True)
    dock.show_context("Workspace → Play → Panel B", "Straight", "Exact order", "Straight")
    assert "Straight" not in dock.detail.toPlainText()
    dock.reset()
    assert not dock.pin.isChecked()
