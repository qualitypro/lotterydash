from pathlib import Path
import pytest
from lotterydash.calibration import ScanPoint
from lotterydash.slip_geometry import SlipCorners, scan_to_slip, save_corners, load_corners

def test_identity_corners():
    c=SlipCorners((0,0),(1,0),(1,1),(0,1))
    assert scan_to_slip(ScanPoint(.25,.75),c)==pytest.approx((.25,.75))

def test_crop_corners():
    c=SlipCorners((.2,.1),(.6,.1),(.6,.9),(.2,.9))
    assert scan_to_slip(ScanPoint(.4,.5),c)==pytest.approx((.5,.5))

def test_skew_corner_mapping():
    c=SlipCorners((.15,.12),(.72,.09),(.76,.91),(.12,.88))
    for src,dst in zip((c.tl,c.tr,c.br,c.bl),((0,0),(1,0),(1,1),(0,1))):
        assert scan_to_slip(ScanPoint(*src),c)==pytest.approx(dst)

def test_save_roundtrip(tmp_path):
    c=SlipCorners((.2,.1),(.7,.1),(.7,.9),(.2,.9))
    p=tmp_path/"corners.json"
    save_corners(p,c)
    assert load_corners(p)==c

def test_invalid_corners():
    with pytest.raises(ValueError):
        SlipCorners((0,0),(0,0),(0,0),(0,0))
