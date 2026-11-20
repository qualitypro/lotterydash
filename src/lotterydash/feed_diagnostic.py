"""Sprint 03J: custom-paper feed and placement diagnostic, not a lottery-slip print."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm
from .print_calibration import WIDTH_IN, HEIGHT_IN

def write_feed_diagnostic(destination):
    """Print on BLANK laser-compatible paper cut to 3.25 x 8.5 inches at 100%."""
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    w, h = WIDTH_IN * inch, HEIGHT_IN * inch
    c = canvas.Canvas(str(target), pagesize=(w, h))
    c.setTitle("LotteryDash 03J BLANK PAPER FEED diagnostic - NOT FOR LOTTERY SLIPS")
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(w / 2, h - 17 * mm, "TOP / PANEL E FIRST")
    c.setFont("Helvetica", 7)
    c.drawCentredString(w / 2, h - 23 * mm, "3.25 x 8.5 in - 100% - no fit")
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(w / 2, 14 * mm, "BOTTOM / PANEL A LAST")
    c.setFont("Helvetica", 7)
    c.drawCentredString(w / 2, 9 * mm, "BLANK TEST PAPER ONLY")
    # Distinct top/bottom reference bars; deliberately inside printable margins.
    c.setLineWidth(1)
    c.line(12 * mm, h - 29 * mm, w - 12 * mm, h - 29 * mm)
    c.line(22 * mm, 22 * mm, w - 22 * mm, 22 * mm)
    # Central 10 mm-spaced ticks, with numbered distance from TOP.
    c.setLineWidth(0.45)
    c.setFont("Helvetica", 7)
    for distance in range(40, 191, 10):
        y = h - distance * mm
        c.line(14 * mm, y, 21 * mm, y)
        c.drawString(24 * mm, y - 2, f"{distance} mm from TOP")
    # Large reference circles at different horizontal positions.
    for label, x, from_top in (("T", 61, 42), ("M", 62, 110), ("B", 61, 177)):
        y = h - from_top * mm
        c.setLineWidth(1)
        c.circle(x * mm, y, 2.5 * mm, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x * mm, y - 1 * mm, label)
    c.save()
    return target
