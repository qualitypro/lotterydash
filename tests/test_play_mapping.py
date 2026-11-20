from decimal import Decimal
from lotterydash.models import Pick3Play
from lotterydash.calibration import ScanPoint
from lotterydash.play_mapping import required_fields, resolve_fields

def test_required_fields_panel_a():
    play = Pick3Play("007", "straight", Decimal("1.00"), "evening")
    assert required_fields(play, "A") == (
        "A.digit1.0", "A.digit2.0", "A.digit3.7",
        "A.straight", "A.amount.1.00", "A.evening"
    )

def test_missing_coordinates_are_reported():
    play = Pick3Play("007")
    points = {"A.digit1.0": ScanPoint(0.1, 0.2)}
    found, missing = resolve_fields(play, "A", points)
    assert list(found) == ["A.digit1.0"]
    assert "A.digit3.7" in missing

def test_all_mapped():
    play = Pick3Play("123")
    points = {key: ScanPoint(0.1, 0.2) for key in required_fields(play, "A")}
    found, missing = resolve_fields(play, "A", points)
    assert len(found) == len(points)
    assert missing == ()

def test_invalid_panel():
    import pytest
    with pytest.raises(ValueError):
        required_fields(Pick3Play("123"), "Z")

def test_existing_panel_a_mapping_names():
    play = Pick3Play("007", "straight", Decimal("1.00"), "evening")
    names = [
        "a.num.col1.0", "a.num.col2.0", "a.num.col3.7",
        "a.type.str", "a.amount.1-dollar", "a.draw-time.eve",
    ]
    points = {name: ScanPoint(0.2, 0.5) for name in names}
    found, missing = resolve_fields(play, "A", points)
    assert set(found) == set(names)
    assert missing == ()
