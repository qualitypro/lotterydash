"""Global detector must never accept missing or ambiguous candidates."""
import pytest

from lotterydash.automap import Candidate
from lotterydash.calibration import ScanPoint
from lotterydash.global_detector import match_globals
from lotterydash.global_options import GLOBAL_FIELDS


def fields():
    return {name: ScanPoint(.1 + i * .04, .2)
            for i, name in enumerate(GLOBAL_FIELDS)}


def test_no_candidates_unresolved():
    confirmed, unresolved, ambiguous = match_globals(fields(), [], 1000, 1000)
    assert confirmed == {}
    assert set(unresolved) == set(GLOBAL_FIELDS)
    assert ambiguous == []


def test_perfect_candidates_confirmed():
    points = fields()
    candidates = [Candidate(p.x * 1000, p.y * 1000, 5)
                  for p in points.values()]
    confirmed, unresolved, ambiguous = match_globals(
        points, candidates, 1000, 1000)
    assert len(confirmed) == 16
    assert not unresolved and not ambiguous


def test_ambiguous_candidate_requires_review():
    points = fields()
    first = next(iter(points.values()))
    candidates = [Candidate(first.x * 1000, first.y * 1000, 5),
                  Candidate(first.x * 1000 + 1, first.y * 1000, 5)]
    confirmed, unresolved, ambiguous = match_globals(
        points, candidates, 1000, 1000)
    name = GLOBAL_FIELDS[0]
    assert name in unresolved
    assert name in ambiguous
    assert name not in confirmed


def test_incomplete_reference_rejected():
    with pytest.raises(ValueError, match="16 global"):
        match_globals({"global.fireball": ScanPoint(.2, .3)}, [], 1000, 1000)
