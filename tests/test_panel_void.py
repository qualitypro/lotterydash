"""Explicit panel activation and void behavior regression tests."""
import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication
from lotterydash.five_panel_editor import FivePanelEditor


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_unchecked_panel_is_void(app):
    editor = FivePanelEditor()
    panel = editor.panels[0]
    assert not panel.enabled.isChecked()
    assert not panel.digits.isEnabled()
    assert panel.get_play() is None
    panel.enabled.setChecked(True)
    panel.digits.setText("007")
    panel.fireball.setChecked(True)
    panel.enabled.setChecked(False)
    assert panel.digits.text() == ""
    assert not panel.fireball.isChecked()
    assert not panel.play_type.isEnabled()
    assert panel.get_play() is None
    assert editor.collect_plays() == []


def test_typing_does_not_activate_void_panel(app):
    editor = FivePanelEditor()
    panel = editor.panels[0]
    panel.digits.setText("123")
    assert not panel.enabled.isChecked()
    assert panel.get_play() is None


def test_active_panel_roundtrip(app):
    editor = FivePanelEditor()
    panel = editor.panels[0]
    panel.enabled.setChecked(True)
    panel.digits.setText("123")
    assert editor.collect_plays()[0].digits == "123"


def test_panel_readiness_states(app):
    editor = FivePanelEditor()
    panel = editor.panels[0]
    assert panel.status.text() == "VOID"
    assert editor.progress.value() == 0
    panel.enabled.setChecked(True)
    assert panel.status.text() == "INCOMPLETE"
    assert editor.progress.value() == 0
    panel.digits.setText("007")
    assert panel.status.text() == "READY"
    assert editor.progress.value() == 1
    panel.enabled.setChecked(False)
    assert panel.status.text() == "VOID"
    assert editor.progress.value() == 0


def test_compact_guide_can_expand_and_collapse(app):
    editor = FivePanelEditor()
    assert not editor.guide.isVisible()
    assert not editor.guide_toggle.isChecked()
    editor.guide_toggle.setChecked(True)
    assert editor.guide_toggle.isChecked()
    assert not editor.guide.isHidden()
    editor.guide_toggle.setChecked(False)
    assert editor.guide.isHidden()
    assert len(editor.panels) == 5
