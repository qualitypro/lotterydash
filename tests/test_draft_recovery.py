"""Sprint 04H: safe saved-draft discovery."""
import os
from pathlib import Path

from lotterydash.calibration import ScanPoint, save_mapping
from lotterydash.draft_recovery import find_latest_draft
from lotterydash.global_options import GLOBAL_FIELDS


def complete_points():
    fields = {f"{p}.num.{i}": ScanPoint(.5, .5)
              for p in "abcde" for i in range(43)}
    fields.update({key: ScanPoint(.25, .25) for key in GLOBAL_FIELDS})
    return fields


def test_missing_directory_returns_none(tmp_path):
    assert find_latest_draft(tmp_path / "missing") is None


def test_skips_incomplete_and_corrupt_drafts(tmp_path):
    old = tmp_path / "old" / "automap-draft.json"
    save_mapping(old, complete_points(), 2550, 3510)
    broken = tmp_path / "new" / "automap-draft.json"
    broken.parent.mkdir()
    broken.write_text("{not-json", encoding="utf-8")
    os.utime(old, (100, 100))
    os.utime(broken, (200, 200))
    assert find_latest_draft(tmp_path) == old


def test_latest_complete_selected(tmp_path):
    first = tmp_path / "first" / "automap-draft.json"
    second = tmp_path / "second" / "automap-draft.json"
    save_mapping(first, complete_points(), 2550, 3510)
    save_mapping(second, complete_points(), 2550, 3510)
    os.utime(first, (100, 100))
    os.utime(second, (200, 200))
    assert find_latest_draft(tmp_path) == second


def test_218_field_draft_not_eligible(tmp_path):
    path = tmp_path / "automap-draft.json"
    points = complete_points()
    for day in range(2, 15):
        points.pop(f"global.days.{day}")
    save_mapping(path, points, 2550, 3510)
    assert find_latest_draft(tmp_path) is None
