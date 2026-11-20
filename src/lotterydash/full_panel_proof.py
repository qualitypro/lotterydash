"""Sprint 03P: all mapped Panel A bubbles, calibration-only proof."""
import argparse
from pathlib import Path
import subprocess
import re

from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas

from .calibration import load_mapping
from .slip_geometry import load_corners, scan_to_slip

PRINTER = "Brother_MFC_9130CW"
OPTIONS = ("media=Custom.3.25x8.5in", "InputSlot=Manual", "print-scaling=none", "sides=one-sided", "copies=1")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Mark every mapped Panel A bubble; NOT a valid lottery entry.")
    parser.add_argument("--mapping", type=Path, default=Path("maps/pick3-mapping.json"))
    parser.add_argument("--output", type=Path, default=Path("images/diagnostics/panel-a-all-bubbles.pdf"))
    parser.add_argument("--expected-count", type=int, default=43)
    parser.add_argument("--diameter-mm", type=float, default=3.0)
    parser.add_argument("--number-grid-y-mm", type=float, default=0.0,
                        help="Additional Y shift for number-grid bubbles; negative moves toward DRAW TIME")
    parser.add_argument("--digits-1-to-5-x-mm", type=float, default=0.0,
                        help="Additional X shift for digit values 1 through 5 in all three columns")
    parser.add_argument("--print", action="store_true", dest="submit")
    args = parser.parse_args(argv)
    if not (0.5 <= args.diameter_mm <= 5.0):
        parser.error("diameter must be between 0.5 and 5.0 mm")
    if not (-5 <= args.number_grid_y_mm <= 5 and -5 <= args.digits_1_to_5_x_mm <= 5):
        parser.error("Group corrections must be within +/-5 mm")
    points = load_mapping(args.mapping)
    panel = {key: value for key, value in points.items() if key.lower().startswith("a.")}
    if len(panel) != args.expected_count:
        raise ValueError(f"Expected {args.expected_count} Panel A bubbles, found {len(panel)}; refusing incomplete test")
    corners = load_corners(args.mapping.with_name("pick3-slip-corners.json"))
    width, height = 3.25 * inch, 8.5 * inch
    radius = args.diameter_mm * mm / 2
    marks = []
    for field, point in sorted(panel.items()):
        u, v = scan_to_slip(point, corners)
        x, y = u * width, (1 - v) * height
        if field.lower() not in ("a.draw-time.eve", "a.evening"):
            x += 1.5 * mm
            y += 1.0 * mm
        if field.lower() in ("a.num.col3.7", "a.digit3.7", "a.amount.1-dollar", "a.amount.1.00"):
            x -= 1.0 * mm
        number_match = re.fullmatch(r"a\\.num\\.col[123]\\.([0-9])", field.lower())
        alternate_match = re.fullmatch(r"a\\.digit[123]\\.([0-9])", field.lower())
        match = number_match or alternate_match
        if match:
            y += args.number_grid_y_mm * mm
            if match.group(1) in "12345":
                x += args.digits_1_to_5_x_mm * mm
        if not (radius <= x <= width-radius and radius <= y <= height-radius):
            raise ValueError(f"Bubble outside page: {field}")
        marks.append((field, x, y))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(args.output), pagesize=(width, height))
    pdf.setTitle("LotteryDash - all Panel A bubbles - calibration only - INVALID ENTRY")
    pdf.setFillColorRGB(0, 0, 0)
    for _, x, y in marks:
        pdf.circle(x, y, radius, stroke=0, fill=1)
    pdf.save()
    print(f"Generated: {args.output.resolve()}")
    print(f"Panel A mapped marks: {len(marks)}")
    print("Calibration: +1.5mm X, +1.0mm Y except EVE; digit 3=7 and $1.00 amount each -1.0mm X")
    print(f"Number-grid Y: {args.number_grid_y_mm:+.2f}mm; digit values 1-5 X: {args.digits_1_to_5_x_mm:+.2f}mm")
    print("WARNING: This is a calibration pattern, NOT a valid lottery entry.")
    if args.submit:
        cmd = ["lp", "-d", PRINTER]
        for option in OPTIONS:
            cmd.extend(["-o", option])
        cmd.append(str(args.output.resolve()))
        subprocess.run(cmd, check=True)
        print("Submitted exactly one print job.")
    else:
        print("DRY RUN: add --print to submit one job.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
