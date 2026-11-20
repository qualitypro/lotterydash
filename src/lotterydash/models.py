"""Validated Pick 3 play selections; no lottery transactions are performed."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class PlayType(str, Enum):
    STRAIGHT = "straight"
    BOX = "box"
    STRAIGHT_BOX = "straight_box"
    COMBO = "combo"
    FRONT_PAIR = "front_pair"
    BACK_PAIR = "back_pair"


class Draw(str, Enum):
    MIDDAY = "midday"
    EVENING = "evening"


@dataclass(frozen=True)
class Pick3Play:
    digits: str
    play_type: PlayType = PlayType.STRAIGHT
    amount: Decimal = Decimal("1.00")
    draw: Draw = Draw.EVENING
    fireball: bool = False

    def __post_init__(self):
        if len(self.digits) != 3 or not all(c in "0123456789" for c in self.digits):
            raise ValueError("Pick 3 requires exactly three digits (000-999)")
        if self.amount not in (Decimal("0.50"), Decimal("1.00")):
            raise ValueError("Supported per-play amounts: $0.50 or $1.00")
        try:
            object.__setattr__(self, "play_type", PlayType(self.play_type))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid play type: {self.play_type!r}") from exc
        try:
            object.__setattr__(self, "draw", Draw(self.draw))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid draw: {self.draw!r}") from exc

MAX_PANELS = 5


def validate_slip(plays: list[Pick3Play]) -> None:
    if not 1 <= len(plays) <= MAX_PANELS:
        raise ValueError("A playslip requires 1 to 5 plays")
