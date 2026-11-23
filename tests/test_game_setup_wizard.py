"""Game setup wizard regression coverage."""
import pytest
from PySide6.QtWidgets import QApplication
from lotterydash.game_setup_wizard import GameSetupWizard, validate_setup
from lotterydash.projects import GAMES, new_project


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_every_game_can_be_configured(app):
    for game in GAMES:
        wizard = GameSetupWizard(initial_game=game)
        assert wizard.project_details()["game"] == game
        assert validate_setup(game, wizard.setup_options()) == wizard.setup_options()
        wizard.close()


def test_pick3_preferences_and_notes(app):
    wizard = GameSetupWizard(initial_game="pick3")
    wizard.name.setText("Friday Pick 3")
    wizard.draw.setCurrentIndex(wizard.draw.findData("midday"))
    wizard.wager.setCurrentIndex(wizard.wager.findData("0.50"))
    wizard.fireball.setChecked(True)
    wizard.notes.setPlainText("Keep for later")
    data = wizard.project_details()
    assert data["game_setup"] == {"draw": "midday", "wager": "0.50", "fireball": True}
    assert data["notes"] == "Keep for later"
    wizard.close()


def test_edit_preserves_game_and_settings(app):
    project = new_project("Existing", "pick3")
    project["game_setup"] = {"draw": "midday", "wager": "0.50", "fireball": True}
    wizard = GameSetupWizard(project=project)
    assert not wizard.game.isEnabled()
    assert wizard.setup_options() == project["game_setup"]
    wizard.close()


def test_reject_invalid_setup():
    with pytest.raises(ValueError):
        validate_setup("pick3", {"draw": "tomorrow"})
    with pytest.raises(ValueError):
        validate_setup("powerball", {"fireball": True})
