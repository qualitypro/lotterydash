"""Sprint 05C: project persistence and production publication guards."""
from pathlib import Path

import pytest

from lotterydash.projects import new_project, save_project, load_project, project_filename
from lotterydash.production_mapping import publish_mapping, validate_for_game


def test_project_roundtrip(tmp_path):
    project = new_project("Pick 3 - First Slip", "pick3")
    project["plays"] = [{"digits": "007", "play_type": "straight",
                         "amount": "1.00", "draw": "evening", "fireball": False}]
    destination = tmp_path / project_filename(project["name"])
    save_project(destination, project)
    assert load_project(destination) == project
    with pytest.raises(FileExistsError):
        save_project(destination, project)


def test_project_games_and_validation():
    for game in ("pick3", "pick4", "powerball"):
        assert new_project("Test", game)["game"] == game
    with pytest.raises(ValueError):
        new_project("Test", "unknown")
    with pytest.raises(ValueError):
        new_project(" ", "pick3")


def test_production_requires_explicit_review(tmp_path):
    with pytest.raises(ValueError, match="review"):
        publish_mapping({"game": "pick3", "project_id": "test"},
                        tmp_path / "missing.json", tmp_path, reviewed=False)


def test_unsupported_game_production_blocked(tmp_path):
    with pytest.raises(ValueError, match="not implemented"):
        validate_for_game("powerball", tmp_path / "missing.json")
