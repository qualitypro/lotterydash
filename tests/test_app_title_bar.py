"""Custom title bar and contextual workspace regression tests."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from lotterydash.main import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_frameless_window_controls_and_context(app):
    window = MainWindow()
    try:
        assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert window.app_title_bar.minimize_button.text() == "−"
        assert window.app_title_bar.close_button.text() == "×"
        assert window.project_menu_button.menu() is not None
        window.tabs.setCurrentIndex(3)
        assert window.context_label.text() == "Workspace: Print / Proof"
    finally:
        window.close()
