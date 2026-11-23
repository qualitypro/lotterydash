"""Find the newest valid AutoMap draft without modifying user files."""
from pathlib import Path

from .calibration import load_mapping
from .global_options import mapping_summary


def find_latest_draft(root, minimum_fields=231):
    """Return newest valid draft meeting field-count and completeness gates.

    A 231-field draft must satisfy the current schema; older 218-field drafts
    remain eligible only when the caller explicitly lowers minimum_fields.
    """
    root = Path(root)
    if not root.is_dir():
        return None
    paths = sorted(root.rglob("automap-draft.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths:
        try:
            points = load_mapping(path)
            summary = mapping_summary(points)
            if len(points) >= minimum_fields and (
                minimum_fields != 231 or summary["complete"]
            ):
                return path
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None
