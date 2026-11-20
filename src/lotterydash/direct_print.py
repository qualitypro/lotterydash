"""Sprint 03L: opt-in, exact-size Brother manual-feed print workflow."""
import argparse
import subprocess
from decimal import Decimal
from pathlib import Path

from .models import Pick3Play
from .print_calibration import PrintCalibration, write_panel_a_marks

PRINTER = "Brother_MFC_9130CW"
OPTIONS = (
    "media=Custom.3.25x8.5in",
    "InputSlot=Manual",
    "print-scaling=none",
    "sides=one-sided",
    "copies=1",
)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate Panel A proof; printing requires --print.")
    parser.add_argument("--mapping", type=Path, default=Path("maps/pick3-mapping.json"))
    parser.add_argument("--output", type=Path, default=Path("images/diagnostics/panel-a-03l.pdf"))
    parser.add_argument("--digits", default="007")
    parser.add_argument("--play-type", default="straight")
    parser.add_argument("--amount", default="1.00")
    parser.add_argument("--draw", default="evening")
    parser.add_argument("--diameter-mm", type=float, default=3.0)
    parser.add_argument("--x-offset-mm", type=float, default=0.0)
    parser.add_argument("--y-offset-mm", type=float, default=0.0)
    parser.add_argument("--print", action="store_true", dest="submit")
    args = parser.parse_args(argv)
    if not (len(args.digits) == 3 and args.digits.isdigit()):
        parser.error("--digits must contain exactly three digits")
    play = Pick3Play(
        digits=args.digits,
        play_type=args.play_type,
        amount=Decimal(args.amount),
        draw=args.draw,
    )
    calibration = PrintCalibration(
        mark_diameter_mm=args.diameter_mm,
        x_offset_mm=args.x_offset_mm,
        y_offset_mm=args.y_offset_mm,
    )
    output = write_panel_a_marks(play, args.output, args.mapping, calibration)
    print(f"Generated: {output.resolve()}")
    print(f"Printer: {PRINTER}; options: {', '.join(OPTIONS)}")
    if not args.submit:
        print("DRY RUN: no print job submitted; pass --print after loading blank test paper.")
        return 0
    command = ["lp", "-d", PRINTER]
    for option in OPTIONS:
        command.extend(["-o", option])
    command.append(str(output.resolve()))
    subprocess.run(command, check=True)
    print("Print job submitted. Inspect blank test paper before using any lottery slip.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
