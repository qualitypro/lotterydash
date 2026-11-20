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
