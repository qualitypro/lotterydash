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

def saved_alias(field: str) -> str:
    panel, remainder = field.split(".", 1)
    prefix = panel.lower()
    if remainder.startswith("digit"):
        position, digit = remainder[5:].split(".", 1)
        return f"{prefix}.num.col{position}.{digit}"
    aliases = {
        "straight": "type.str",
        "box": "type.box",
        "straight_box": "type.str-box",
        "combo": "type.combo",
        "front_pair": "type.front-pair",
        "back_pair": "type.back-pair",
        "amount.1.00": "amount.1-dollar",
        "amount.0.50": "amount.half-dollar",
        "midday": "draw-time.mid",
        "evening": "draw-time.eve",
    }
    return f"{prefix}.{aliases.get(remainder, remainder)}"

def resolve_fields(play: Pick3Play, panel: str, points: dict[str, ScanPoint]):
    found = {}
    missing = []
    for field in required_fields(play, panel):
        match = next((key for key in (field, saved_alias(field)) if key in points), None)
        if match is None:
            missing.append(field)
        else:
            found[match] = points[match]
    return found, tuple(missing)
