"""Letter-size Panel A alignment proof; never a direct-slip print instruction."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm

from .calibration import load_mapping
from .slip_geometry import load_corners, scan_to_slip
from .play_mapping import resolve_fields
from .print_calibration import PrintCalibration, WIDTH_IN, HEIGHT_IN

LETTER_WIDTH = 8.5 * inch
LETTER_HEIGHT = 11 * inch
SLIP_WIDTH = WIDTH_IN * inch
SLIP_HEIGHT = HEIGHT_IN * inch
LEFT = (LETTER_WIDTH - SLIP_WIDTH) / 2
BOTTOM = (LETTER_HEIGHT - SLIP_HEIGHT) / 2

def write_letter_panel_a_proof(play, destination, mapping_path, calibration=None):
    """Place a 3.25 x 8.5-inch slip footprint centered on US Letter.

    Positions assume saved normalized coordinates refer to the slip edges.
    If the source scan has margins, correct the scan-to-slip transform before
    trusting alignment. Never infer support for feeding physical slips.
    """
    settings = calibration if calibration is not None else PrintCalibration()
    found, missing = resolve_fields(play, "A", load_mapping(mapping_path))
    if missing:
        raise ValueError("Missing Panel A coordinates: " + ", ".join(missing))
    corners_path = Path(mapping_path).with_name("pick3-slip-corners.json")
    if not corners_path.is_file():
        raise ValueError(f"Four-corner calibration required: {corners_path}")
    corners = load_corners(corners_path)
    radius = settings.mark_diameter_mm * mm / 2
    marks = []
    for point in found.values():
        u, v = scan_to_slip(point, corners)
        x = LEFT + u * SLIP_WIDTH * settings.x_scale + settings.x_offset_mm * mm
        y = BOTTOM + (1 - v) * SLIP_HEIGHT * settings.y_scale + settings.y_offset_mm * mm
        if not (radius <= x <= LETTER_WIDTH - radius and radius <= y <= LETTER_HEIGHT - radius):
            raise ValueError("Calibrated mark is outside letter page")
        marks.append((x, y))

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(target), pagesize=(LETTER_WIDTH, LETTER_HEIGHT))
    pdf.setTitle("LotteryDash Panel A US Letter alignment proof - NOT printer calibrated")
    # Thin footprint outline and corner ticks for positioning an actual slip
    # over a letter-size test print; the outline is NOT part of the slip marks.
    pdf.setStrokeColorRGB(0.55, 0.55, 0.55)
    pdf.setLineWidth(0.4)
    pdf.setDash(3, 3)
    pdf.rect(LEFT, BOTTOM, SLIP_WIDTH, SLIP_HEIGHT, stroke=1, fill=0)
    pdf.setDash()
    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setFillColorRGB(0, 0, 0)
    for x, y in marks:
        pdf.circle(x, y, radius, stroke=0, fill=1)
    pdf.save()
    return target
