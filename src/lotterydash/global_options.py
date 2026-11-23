"""Global playslip selections outside the five repeated Pick 3 panels.

These are semantic field IDs, not guessed coordinates. Their centers require
image-based review and explicit placement until a verified detector exists.
"""
GLOBAL_FIELDS = (
    "global.fireball",
    "global.quick-picks.10-dollar",
    "global.quick-picks.5-dollar",
    *(f"global.days.{day}" for day in range(2, 15)),
)


def validate_global_fields(points):
    """Require all global fields before approving a complete playslip."""
    missing = [name for name in GLOBAL_FIELDS if name not in points]
    if missing:
        raise ValueError("Missing global fields: " + ", ".join(missing))
    return True


def mapping_summary(points):
    panel_counts = {name: 0 for name in "abcde"}
    for key in points:
        prefix = key.split(".", 1)[0]
        if prefix in panel_counts:
            panel_counts[prefix] += 1
    globals_present = [name for name in GLOBAL_FIELDS if name in points]
    return {
        "expected_fields": 231,
        "mapped_fields": len(points),
        "panel_counts": panel_counts,
        "global_mapped": globals_present,
        "global_missing": [name for name in GLOBAL_FIELDS if name not in points],
        "complete": all(count == 43 for count in panel_counts.values())
                    and len(globals_present) == len(GLOBAL_FIELDS) and len(points) == 231,
    }
