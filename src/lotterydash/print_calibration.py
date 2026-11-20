"""Panel A marks-only PDF calibration; physical printer alignment is unverified."""
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path
import json

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm

from .calibration import load_mapping
from .play_mapping import resolve_fields
from .slip_geometry import load_corners, scan_to_slip

WIDTH_IN = 3.25
HEIGHT_IN = 8.5

@dataclass(frozen=True)
class PrintCalibration:
    x_offset_mm: float = 0.0
    y_offset_mm: float = 0.0
    x_scale: float = 1.0
    y_scale: float = 1.0
    mark_diameter_mm: float = 2.0

    def __post_init__(self):
        for value in (self.x_offset_mm, self.y_offset_mm, self.x_scale, self.y_scale, self.mark_diameter_mm):
            if not (-1000 < value < 1000):
                raise ValueError("Invalid calibration value")
        if not (0.90 <= self.x_scale <= 1.10 and 0.90 <= self.y_scale <= 1.10):
            raise ValueError("Calibration scale must be between 90% and 110%")
        if not (0.5 <= self.mark_diameter_mm <= 5.0):
            raise ValueError("Mark diameter must be 0.5–5 mm")
        if not (-20 <= self.x_offset_mm <= 20 and -20 <= self.y_offset_mm <= 20):
            raise ValueError("Offset must be within ±20 mm")

def save_calibration(path, calibration):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(calibration), indent=2) + "\n", encoding="utf-8")

def load_calibration(path):
    return PrintCalibration(**json.loads(Path(path).read_text(encoding="utf-8")))

def write_panel_a_marks(play, destination, mapping_path, calibration=None, non_eve_x_mm=0.0, non_eve_y_mm=0.0, digit3_x_mm=0.0, amount_x_mm=0.0):
    """Optional offsets affect all selected marks except the evening draw bubble."""
    if not (-20 <= non_eve_x_mm <= 20 and -20 <= non_eve_y_mm <= 20):
        raise ValueError("Selective offsets must be within ±20 mm")
    if not (-20 <= digit3_x_mm <= 20 and -20 <= amount_x_mm <= 20):
        raise ValueError("Per-bubble offsets must be within ±20 mm")
    calibration = calibration or PrintCalibration()
    points = load_mapping(mapping_path)
    found, missing = resolve_fields(play, "A", points)
    if missing:
        raise ValueError("Missing Panel A coordinates: " + ", ".join(missing))
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    width, height = WIDTH_IN * inch, HEIGHT_IN * inch
    pdf = canvas.Canvas(str(target), pagesize=(width, height))
    pdf.setTitle("LotteryDash Panel A marks-only calibration - NOT VERIFIED FOR PRINTING")
    pdf.setFillColorRGB(0, 0, 0)
    corners_path = Path(mapping_path).with_name("pick3-slip-corners.json")
    if not corners_path.is_file():
        raise ValueError(f"Four-corner calibration required: {corners_path}")
    corners = load_corners(corners_path)
    radius = calibration.mark_diameter_mm * mm / 2
    for field, point in found.items():
        u, v = scan_to_slip(point, corners)
        x = u * width * calibration.x_scale + calibration.x_offset_mm * mm
        y = (1 - v) * height * calibration.y_scale + calibration.y_offset_mm * mm
        if field.lower() not in ("a.draw-time.eve", "a.evening"):
            x += non_eve_x_mm * mm
            y += non_eve_y_mm * mm
        if field.lower() in ("a.num.col3.7", "a.digit3.7"):
            x += digit3_x_mm * mm
        if field.lower() in ("a.amount.1-dollar", "a.amount.1.00"):
            x += amount_x_mm * mm
        if not (radius <= x <= width - radius and radius <= y <= height - radius):
            raise ValueError("A mark falls outside the page; adjust calibration")
        pdf.circle(x, y, radius, stroke=0, fill=1)
    pdf.save()
    return target
