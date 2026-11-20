"""Scan-aligned visual PDF proof. Not calibrated for official slip printing."""
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

from .calibration import load_mapping
from .models import validate_slip
from .play_mapping import resolve_fields


def write_mapped_preview(plays, destination, scan_path, mapping_path):
    validate_slip(plays)
    scan_path = Path(scan_path)
    mapping_path = Path(mapping_path)
    if not scan_path.is_file() or not mapping_path.is_file():
        raise ValueError("Scanned image and saved mapping are required")
    points = load_mapping(mapping_path)
    selections = {}
    missing = []
    for index, play in enumerate(plays):
        found, absent = resolve_fields(play, "ABCDE"[index], points)
        selections.update(found)
        missing.extend(absent)
    if missing:
        raise ValueError("Unmapped selections: " + ", ".join(missing))
    with Image.open(scan_path) as image:
        width, height = image.size
        if width <= 0 or height <= 0:
            raise ValueError("Invalid scan dimensions")
        image.load()
        pdf = canvas.Canvas(str(destination), pagesize=(width, height))
        pdf.setTitle("LotteryDash scan-aligned visual proof - NOT printer calibrated")
        pdf.drawImage(ImageReader(image), 0, 0, width=width, height=height)
        pdf.setFillColorRGB(0.9, 0, 0)
        pdf.setStrokeColorRGB(0.9, 0, 0)
        for point in selections.values():
            pdf.circle(point.x * width, (1 - point.y) * height, 8, stroke=1, fill=1)
        pdf.save()
    return Path(destination)
