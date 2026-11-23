"""Last selected Florida Lottery game persists between application windows."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])

from lotterydash.main import MainWindow


def test_last_game_restored(app, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    QSettings("LotteryDash", "LotteryDash").clear()
    first = MainWindow()
    try:
        index = first.game_selector.findData("fantasy5")
        assert index >= 0
        first.game_selector.setCurrentIndex(index)
        assert QSettings("LotteryDash", "LotteryDash").value("workspace/last_game") == "fantasy5"
    finally:
        first.close()
    second = MainWindow()
    try:
        assert second.game_selector.currentData() == "fantasy5"
    finally:
        second.close()
