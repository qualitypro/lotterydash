"""Template recovery tests using synthetic boxed symbols."""
import numpy as np
import cv2

from lotterydash.box_recovery import recover_box, recover_exceptions
from lotterydash.calibration import ScanPoint


def _scene():
    image = np.full((350, 250), 235, dtype=np.uint8)
    # A distinct boxed pattern, copied into another panel.
    cv2.rectangle(image, (100, 235), (130, 265), 60, 2)
    cv2.line(image, (105, 244), (124, 244), 35, 2)
    cv2.circle(image, (114, 253), 5, 85, 2)
    image[65:96, 101:132] = image[235:266, 100:131]
    return image


def test_template_recovers_shifted_box():
    image = _scene()
    result = recover_box(image, 115, 250, 115, 80,
                         min_score=.6, min_margin=.01)
    assert result is not None
    assert abs(result.x - 116) <= 1
    assert abs(result.y - 80) <= 1


def test_blank_target_rejected():
    image = _scene()
    result = recover_box(image, 115, 250, 180, 80,
                         min_score=.9)
    assert result is None


def test_exception_recovery_rejects_unverified_image():
    image = np.full((350, 250), 235, dtype=np.uint8)
    fields = {"a.draw-time.mid": ScanPoint(115/250, 250/350)}
    panels = {"B": {"dx": 0, "dy": -170,
                    "missing": ["a.draw-time.mid"], "ambiguous": []}}
    recovered, unresolved = recover_exceptions(
        image, fields, panels, 250, 350)
    assert recovered == {}
    assert unresolved == ["b.draw-time.mid"]
