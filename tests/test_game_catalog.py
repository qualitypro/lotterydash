"""Florida draw-game catalog and project compatibility tests."""
from lotterydash.projects import GAMES, GAME_GROUPS, IMPLEMENTED_EDITORS, new_project, validate_project


def test_current_florida_draw_games_are_selectable():
    expected = {
        "pick2", "pick3", "pick4", "pick5", "fantasy5", "cashpop",
        "floridalotto", "jackpottripleplay", "powerball", "megamillions",
    }
    assert set(GAMES) == expected
    assert set().union(*(set(codes) for codes in GAME_GROUPS.values())) == expected


def test_all_games_can_have_projects():
    for game in GAMES:
        assert validate_project(new_project("Example", game))["game"] == game


def test_only_implemented_editor_is_marked_ready():
    assert IMPLEMENTED_EDITORS == {"pick3"}
