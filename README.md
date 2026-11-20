# LotteryDash

Local-first Florida Pick 3 play planner and experimental print-calibration project for Brother MFC-9130CW.

## Status

**Sprint 01 prototype** on `feature/sprint01-foundation`. Native Qt application with five-panel play entry and a clearly labeled **draft letter-size PDF** export. Direct printing on official lottery playslips is **not implemented or validated**.

## Features

- PySide6 native desktop interface
- Three-digit entry with leading zeros
- Straight, Box, Straight/Box, Combo, Front Pair and Back Pair data models
- Midday / Evening selection
- $0.50 / $1.00 play amounts
- Five-panel validation
- ReportLab draft PDF preview
- pytest validation tests

Fireball, multi-day selections, persistence, calibration, CUPS and batch printing remain future work.

## Requirements

- Python 3.10+
- PySide6 6.6+
- ReportLab 4+
- pytest 8+ for development
- CUPS for future printer integration

## Fedora installation

```bash
git clone https://github.com/qualitypro/lotterydash.git
cd lotterydash
git switch feature/sprint01-foundation
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
lotterydash
```

## Roadmap

1. Foundation: app shell, models, draft export and tests
2. Scan-based playslip geometry and calibration
3. CUPS detection and plain-paper alignment testing
4. Saved plays and batch job management with hardware safety checks
5. Packaging, documentation and QA

## Media and validation warning

The Brother printer uses a heated laser fuser. Official lottery slips may have incompatible stock or preprinted inks. Do not run them through the printer until compatibility is verified. The main tray is not confirmed to accept narrow slips, and terminal scanner acceptance is unverified. Photograph-based dimensions are approximate; calibrate using physical measurements and a flatbed scan. This application does not purchase lottery tickets.

## License

No license has been selected.
