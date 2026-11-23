"""Full ballot wizard: translated coordinates remain drafts and source is untouched."""
import pytest
from lotterydash.calibration import ScanPoint
from lotterydash.full_ballot_mapper import replicate_panel


def sample_panel():
    return {f"a.num.col1.{n}": ScanPoint(.1 + n * .01, .2) for n in range(10)} | {
        f"a.other.{n}": ScanPoint(.2, .25 + n * .005) for n in range(33)
    }


def test_replication_preserves_43_and_source():
    original = sample_panel()
    draft = replicate_panel(original, "b", "a.num.col1.0", ScanPoint(.2, .4))
    assert len(draft) == 43
    assert draft["b.num.col1.0"] == ScanPoint(.2, .4)
    assert draft["b.num.col1.1"].x == pytest.approx(.21)
    assert len(original) == 43
    assert not any(k.startswith("b.") for k in original)


def test_reject_incomplete_panel():
    with pytest.raises(ValueError, match="43"):
        replicate_panel({"a.num.0": ScanPoint(.1, .1)}, "b",
                        "a.num.0", ScanPoint(.2, .2))


def test_reject_bad_target():
    with pytest.raises(ValueError, match="Target"):
        replicate_panel(sample_panel(), "a", "a.num.col1.0",
                        ScanPoint(.2, .2))


def test_reject_out_of_bounds():
    with pytest.raises(ValueError, match="outside"):
        replicate_panel(sample_panel(), "c", "a.num.col1.0",
                        ScanPoint(.99, .99))
