"""Sprint 04B: discover repeated Pick 3 panels using verified Panel A geometry.

Never modifies the source map. Every inferred field must match a detected
candidate; panel labels and proposed coordinates require human approval.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .automap import Candidate, _cv, _load_gray, detect_candidates, match_fields
from .calibration import ScanPoint, load_mapping, save_mapping

PANELS = "ABCDE"


def shifted_fields(fields, dx, dy, width, height):
    return {name: ScanPoint((point.x * width + dx) / width,
                            (point.y * height + dy) / height)
            for name, point in fields.items()
            if 0 <= point.x * width + dx <= width and
               0 <= point.y * height + dy <= height}


def score_shift(fields, candidates, width, height, dx, dy, tolerance):
    shifted = shifted_fields(fields, dx, dy, width, height)
    if len(shifted) != len(fields):
        return 0, float("inf"), {}, [], []
    assigned, missing, ambiguous = match_fields(
        shifted, candidates, width, height, tolerance)
    distances = [d for _, d in assigned.values()]
    return len(assigned), sum(distances) / len(distances) if distances else float("inf"), assigned, missing, ambiguous


def discover_panels(fields, candidates, width, height, tolerance=6, expected=5):
    """Find repeated panels by voting for vertical translations from Panel A.

    Requires strong coverage at each position and a regular panel pitch.
    Does not assume an exact pixel spacing or copy positions without detection.
    """
    if not 1 <= expected <= 5:
        raise ValueError("expected panels must be between 1 and 5")
    if not 0 < tolerance <= 12:
        raise ValueError("tolerance must be between 0 and 12 pixels")
    if not fields:
        raise ValueError("Panel A reference mapping is empty")

    base = score_shift(fields, candidates, width, height, 0, 0, tolerance)
    if base[0] < math.ceil(len(fields) * .85):
        raise ValueError(f"Panel A reference verification insufficient: {base[0]}/{len(fields)}")

    # A repeated panel is normally above A in the supplied scan. Discover
    # its pitch from candidate y offsets, while restricting horizontal drift.
    votes = {}
    for point in fields.values():
        px, py = point.x * width, point.y * height
        for candidate in candidates:
            dx, dy = candidate.x - px, candidate.y - py
            if abs(dx) <= 10 and -height * .65 <= dy <= -40:
                bin_y = round(dy / 3) * 3
                votes[bin_y] = votes.get(bin_y, 0) + 1

    # Score candidate offsets against *all* fields, not just a single bubble.
    scored = []
    for center, _ in sorted(votes.items(), key=lambda item: -item[1])[:100]:
        for dy in range(center - 3, center + 4):
            for dx in range(-5, 6, 2):
                n, error, assigned, missing, ambiguous = score_shift(
                    fields, candidates, width, height, dx, dy, tolerance)
                if n >= math.ceil(len(fields) * .85):
                    scored.append((n, -error, dx, dy, assigned, missing, ambiguous))

    # Greedy distinct offsets; disallow duplicate panels at nearby y values.
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    selected = [(0, 0, base)]
    for n, neg_error, dx, dy, assigned, missing, ambiguous in scored:
        if all(abs(dy - existing_y) > 35 for _, existing_y, _ in selected):
            selected.append((dx, dy, (n, -neg_error, assigned, missing, ambiguous)))
            if len(selected) == expected:
                break

    # A is lowest in the image. Assign names by ascending y offset.
    selected.sort(key=lambda entry: entry[1], reverse=True)
    panels = {}
    for index, (dx, dy, result) in enumerate(selected):
        if index >= len(PANELS):
            break
        n, error, assigned, missing, ambiguous = result
        panels[PANELS[index]] = {
            "dx": dx, "dy": dy, "matched": n, "mean_distance_px": round(error, 3),
            "missing": missing, "ambiguous": ambiguous,
            "assigned": assigned,
        }
    return panels


def run(image, mapping, output_dir, tolerance=6, expected=5,
        min_radius=4, max_radius=32):
    cv2 = _cv()
    gray = _load_gray(image)
    height, width = gray.shape
    original = load_mapping(mapping)
    fields = {k: v for k, v in original.items() if k.lower().startswith("a.")}
    candidates = detect_candidates(gray, min_radius, max_radius)
    panels = discover_panels(fields, candidates, width, height, tolerance, expected)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    preview = cv2.imread(str(image))
    proposed = {}
    details = {}
    for name, panel in panels.items():
        assigned = panel["assigned"]
        # The semantic suffix is retained, but all new panel identities are
        # provisional until the user checks the panel labels on the overlay.
        for field, (candidate, distance) in assigned.items():
            new_field = name.lower() + field[1:]
            if not (0 <= candidate.x <= width and 0 <= candidate.y <= height):
                continue
            proposed[new_field] = ScanPoint(candidate.x / width, candidate.y / height)
            cv2.circle(preview, (round(candidate.x), round(candidate.y)),
                       6, (0, 180, 0), 2)
        for field in panel["missing"]:
            p = fields[field]
            x = round(p.x * width + panel["dx"])
            y = round(p.y * height + panel["dy"])
            cv2.circle(preview, (x, y), 8, (0, 0, 255), 2)
        anchor = next(iter(fields.values()))
        label_x = max(0, min(width - 70, round(anchor.x * width + panel["dx"])))
        label_y = max(20, min(height - 10, round(anchor.y * height + panel["dy"] - 35)))
        cv2.putText(preview, f"Panel {name}: {panel['matched']}/{len(fields)}",
                    (label_x, label_y), cv2.FONT_HERSHEY_SIMPLEX,
                    .55, (0, 100, 200), 2)
        details[name] = {
            k: v for k, v in panel.items() if k != "assigned"
        }
        details[name]["missing"] = [
            name.lower() + key[1:] for key in panel["missing"]
        ]
        details[name]["ambiguous"] = [
            name.lower() + key[1:] for key in panel["ambiguous"]
        ]
    complete = (len(panels) == expected and
                all(p["matched"] == len(fields) and
                    not p["ambiguous"] for p in panels.values()))
    report = {
        "status": "review_required", "approved": False,
        "complete_detection": complete,
        "source_image": str(image), "reference_mapping": str(mapping),
        "detected_candidates": len(candidates),
        "expected_panels": expected, "discovered_panels": len(panels),
        "expected_fields": expected * len(fields),
        "matched_fields": len(proposed), "panels": details,
    }
    (output_dir / "full-slip-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not cv2.imwrite(str(output_dir / "full-slip-overlay.png"), preview):
        raise OSError("Could not write overlay")
    if complete:
        save_mapping(output_dir / "full-slip-proposed.json",
                     proposed, width, height)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Discover repeated panels; review required")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, default=Path("maps/pick3-mapping.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("images/diagnostics/full-slip-automap"))
    parser.add_argument("--tolerance-px", type=float, default=6)
    parser.add_argument("--expected-panels", type=int, default=5)
    parser.add_argument("--min-radius", type=int, default=4)
    parser.add_argument("--max-radius", type=int, default=32)
    args = parser.parse_args(argv)
    report = run(args.image, args.mapping, args.output_dir,
                 args.tolerance_px, args.expected_panels,
                 args.min_radius, args.max_radius)
    print(json.dumps(report, indent=2))
    print(f"Review files in {args.output_dir}; original mapping unchanged")
    return 0 if report["complete_detection"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
