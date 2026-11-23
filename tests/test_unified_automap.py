"""Unified mapping merge must be complete, disjoint and review-only."""
import pytest

from lotterydash.calibration import ScanPoint
from lotterydash.global_options import GLOBAL_FIELDS
from lotterydash.unified_automap import combine_proposals


def panel_points():
    return {f"{panel}.field.{i}": ScanPoint(.2, .3)
            for panel in "abcde" for i in range(43)}


def global_points():
    return {name: ScanPoint(.4, .5) for name in GLOBAL_FIELDS}


def test_merge_231_complete():
    result = combine_proposals(panel_points(), global_points())
    assert len(result) == 231
    assert set(GLOBAL_FIELDS).issubset(result)


def test_merge_rejects_missing_global():
    globals_ = global_points()
    globals_.pop(GLOBAL_FIELDS[0])
    with pytest.raises(ValueError, match="Incomplete"):
        combine_proposals(panel_points(), globals_)


def test_merge_rejects_duplicate():
    panels = panel_points()
    panels[GLOBAL_FIELDS[0]] = ScanPoint(.1, .2)
    with pytest.raises(ValueError, match="Duplicate"):
        combine_proposals(panels, global_points())


def test_merge_rejects_bad_panel_distribution():
    panels = panel_points()
    panels.pop("e.field.42")
    panels["e.extra.42"] = ScanPoint(.1, .2)
    with pytest.raises(ValueError, match="Incomplete"):
        combine_proposals(panels, global_points())
