"""Full-slip discovery synthetic tests; no printer or scanned assets required."""
from lotterydash.automap import Candidate
from lotterydash.calibration import ScanPoint
from lotterydash.full_slip_automap import discover_panels, shifted_fields


def test_shifted_fields_coordinates():
    fields = {"a.num.col1.0": ScanPoint(.2, .6)}
    shifted = shifted_fields(fields, 0, -100, 1000, 1000)
    assert abs(shifted["a.num.col1.0"].y - .5) < 1e-9


def test_five_repeated_panels():
    fields = {
        f"a.num.col{col}.{digit}":
            ScanPoint((100 + col * 25) / 1000, (650 + digit * 8) / 1000)
        for col in range(1, 4) for digit in range(10)
    }
    candidates = []
    for panel in range(5):
        for p in fields.values():
            candidates.append(Candidate(p.x * 1000, p.y * 1000 - panel * 110, 5))
    panels = discover_panels(fields, candidates, 1000, 1000, 3, 5)
    assert list(panels) == list("ABCDE")
    assert all(p["matched"] == len(fields) for p in panels.values())


def test_requires_reference_panel():
    import pytest
    fields = {"a.num.col1.0": ScanPoint(.1, .6)}
    with pytest.raises(ValueError, match="Panel A reference verification"):
        discover_panels(fields, [], 1000, 1000)
