"""Panel A marks-only PDF calibration; physical printer alignment is unverified."""
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path
import json

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm

from .calibration import load_mapping
from .play_mapping import resolve_fields

WIDTH_IN = 4.25
HEIGHT_IN = 9.5

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

def write_panel_a_marks(play, destination, mapping_path, calibration=None):
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
    radius = calibration.mark_diameter_mm * mm / 2
    for point in found.values():
        x = point.x * width * calibration.x_scale + calibration.x_offset_mm * mm
        y = (1 - point.y) * height * calibration.y_scale + calibration.y_offset_mm * mm
        if not (radius <= x <= width - radius and radius <= y <= height - radius):
            raise ValueError("A mark falls outside the page; adjust calibration")
        pdf.circle(x, y, radius, stroke=0, fill=1)
    pdf.save()
    return target
