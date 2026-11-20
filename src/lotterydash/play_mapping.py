"""Resolve saved bubble IDs to Pick 3 selections without guessing coordinates."""
from .models import Pick3Play
from .calibration import ScanPoint

def required_fields(play: Pick3Play, panel: str) -> tuple[str, ...]:
    panel = panel.upper()
    if panel not in "ABCDE" or len(panel) != 1:
        raise ValueError("Panel must be A through E")
    fields = [f"{panel}.digit{position}.{digit}" for position, digit in enumerate(play.digits, 1)]
    fields.append(f"{panel}.{play.play_type.value}")
    fields.append(f"{panel}.amount.{play.amount:.2f}")
    fields.append(f"{panel}.{play.draw.value}")
    if play.fireball:
        fields.append(f"{panel}.fireball")
    return tuple(fields)

def resolve_fields(play: Pick3Play, panel: str, points: dict[str, ScanPoint]):
    required = required_fields(play, panel)
    return ({key: points[key] for key in required if key in points},
            tuple(key for key in required if key not in points))
