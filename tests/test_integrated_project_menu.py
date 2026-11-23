"""Integrated project menu retains the existing project commands."""
import pytest
from PySide6.QtWidgets import QApplication
from lotterydash.main import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_compact_header_project_menu(app):
    window = MainWindow()
    try:
        menu = window.project_menu_button.menu()
        assert menu is not None
        labels = [action.text() for action in menu.actions()]
        assert labels == [
            "New Project…", "Open Project…", "Game Setup…",
            "Save Project", "Save Project As…",
        ]
        assert window.game_selector.count() == 10
        assert window.game_notice.isHidden()
    finally:
        window.close()
