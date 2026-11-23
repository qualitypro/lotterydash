# Sprint 04A — AutoMap (experimental)

AutoMap is a **non-destructive, template-guided** playslip detector. It does
not yet autonomously infer arbitrary game rules or guarantee 43 correctly
recognized bubbles. A human must review the proposed field centers.

## Installation

Install the project as usual, then install the optional image processing extra:

```bash
.venv/bin/python -m pip install 'opencv-python-headless>=4.8'
```

## Run against the original scan

```bash
.venv/bin/python -m lotterydash.automap \
  --image images/pick3-playslip.png \
  --mapping maps/pick3-mapping.json \
  --panel a \
  --output-dir images/diagnostics/automap-04a
```

For a **different scan of the same playslip**, supply
`--reference-image images/pick3-playslip.png` to estimate perspective
registration. If registration cannot be established reliably, AutoMap stops
rather than guessing.

Output:

- `automap-report.json`: expected, matched, missing and ambiguous fields
- `automap-overlay.png`: visual review overlay (green matches, red missing)
- `automap-proposed.json`: only emitted when every expected field is matched
  without flagged ambiguity; **not automatically approved**

AutoMap returns exit code 2 for incomplete detection, allowing QA scripts to
distinguish a review-required result from a complete proposal.

The original `maps/pick3-mapping.json`, `maps/pick3-slip-corners.json`,
image assets, and printer-specific offsets are never modified.

## Current limitations

- Requires a known semantic mapping for matching field identities.
- Circular contour detection may miss non-circular boxes or confuse letters
  and artwork for bubbles; review is mandatory.
- Matching tolerance and bubble radius are measured in reference image pixels.
- Other games, multi-panel discovery, semantic OCR and interactive editing
  are planned for subsequent Sprint 04 phases.
- No calibration-only proof is a valid lottery entry.
