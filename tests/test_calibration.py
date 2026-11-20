import json
import pytest
from lotterydash.calibration import ScanPoint, normalize, to_pixels, save_mapping, load_mapping


def test_normalization_round_trip():
    point = normalize(300, 500, 1487, 2047)
    x, y = to_pixels(point, 1487, 2047)
    assert x == pytest.approx(300)
    assert y == pytest.approx(500)


@pytest.mark.parametrize("x,y", [(-0.1, 0.5), (1.1, 0.5), (0.5, -1), (0.5, 2)])
def test_outside_image_rejected(x, y):
    with pytest.raises(ValueError):
        ScanPoint(x, y)


def test_zero_dimensions_rejected():
    with pytest.raises(ValueError):
        normalize(1, 1, 0, 200)


def test_mapping_persistence(tmp_path):
    path = tmp_path / "map.json"
    save_mapping(path, {"A.digit1.7": ScanPoint(0.2, 0.4)}, 1487, 2047)
    assert load_mapping(path)["A.digit1.7"] == ScanPoint(0.2, 0.4)
    assert json.loads(path.read_text())["physical_dimensions_verified"] is False


def test_schema_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version": 999, "points": {}}')
    with pytest.raises(ValueError):
        load_mapping(path)
