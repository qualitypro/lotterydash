from decimal import Decimal
import pytest

from lotterydash.models import Draw, Pick3Play, PlayType, validate_slip


def test_leading_zeroes_preserved():
    assert Pick3Play("007").digits == "007"


@pytest.mark.parametrize("digits", ["12", "1234", "1a2", "", "１２３"])
def test_invalid_digits(digits):
    with pytest.raises(ValueError):
        Pick3Play(digits)


def test_valid_options():
    play = Pick3Play("000", PlayType.BOX, Decimal("0.50"), Draw.MIDDAY)
    assert play.amount == Decimal("0.50")


def test_invalid_amount():
    with pytest.raises(ValueError):
        Pick3Play("123", amount=Decimal("2.00"))


def test_five_panel_limit():
    validate_slip([Pick3Play("123")] * 5)
    with pytest.raises(ValueError):
        validate_slip([Pick3Play("123")] * 6)


def test_qt_string_values_are_normalized():
    play = Pick3Play("007", "straight", Decimal("1.00"), "evening")
    assert play.play_type is PlayType.STRAIGHT
    assert play.draw is Draw.EVENING


@pytest.mark.parametrize("field,value", [
    ("play_type", "invalid"),
    ("draw", "invalid"),
    ("play_type", None),
    ("draw", None),
])
def test_invalid_enum_values_have_specific_error(field, value):
    with pytest.raises(ValueError, match=f"Invalid {field}"):
        Pick3Play("123", **{field: value})
