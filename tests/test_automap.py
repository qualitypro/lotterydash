"""AutoMap matching tests; no OpenCV required for matching logic."""
from lotterydash.automap import Candidate, match_fields
from lotterydash.calibration import ScanPoint


def test_unique_nearest_matching():
    fields = {"a.num.col1.0": ScanPoint(.2, .3),
              "a.num.col1.1": ScanPoint(.2, .4)}
    candidates = [Candidate(20.5, 30.5, 4), Candidate(20, 40, 4)]
    assigned, missing, ambiguous = match_fields(fields, candidates, 100, 100, 4)
    assert len(assigned) == 2
    assert missing == []
    assert ambiguous == []


def test_missing_fields_flagged():
    fields = {"a.num.col1.0": ScanPoint(.2, .3)}
    assigned, missing, ambiguous = match_fields(fields, [], 100, 100, 4)
    assert assigned == {}
    assert missing == ["a.num.col1.0"]
    assert ambiguous == []


def test_close_alternative_requires_review():
    fields = {"a.num.col1.0": ScanPoint(.2, .3)}
    candidates = [Candidate(20, 30, 4), Candidate(21, 30, 4)]
    assigned, missing, ambiguous = match_fields(fields, candidates, 100, 100, 4)
    assert len(assigned) == 1
    assert not missing
    assert ambiguous == ["a.num.col1.0"]


def test_invalid_tolerance():
    import pytest
    with pytest.raises(ValueError):
        match_fields({}, [], 100, 100, 0)
