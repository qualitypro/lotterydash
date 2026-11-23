"""Sprint 04H Phase 2A: conservative global-field detection.

Requires a user-reviewed 231-field reference mapping. Never copies reference
coordinates as successful detections, and never changes printing calibration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .automap import (_cv, _load_gray, detect_candidates, match_fields,
                      register_to_reference, Candidate)
from .calibration import ScanPoint, load_mapping, save_mapping
from .global_options import GLOBAL_FIELDS, mapping_summary


def match_globals(fields, candidates, width, height, tolerance_px=12):
    """Return confirmed matches, unresolved IDs and ambiguous IDs."""
    if set(fields) != set(GLOBAL_FIELDS):
        raise ValueError("Reference must contain all 16 global fields")
    assigned, missing, ambiguous = match_fields(
        fields, candidates, width, height, tolerance_px)
    # An ambiguous match is never considered confirmed.
    confirmed = {name: value for name, value in assigned.items()
                 if name not in ambiguous}
    return confirmed, sorted(set(missing) | set(ambiguous)), ambiguous


def run(image, mapping, output_dir, reference_image=None, tolerance_px=12):
    cv2 = _cv()
    points = load_mapping(mapping)
    if not mapping_summary(points)["complete"]:
        raise ValueError("A complete 231-field reference draft is required")
    fields = {name: points[name] for name in GLOBAL_FIELDS}
    gray = _load_gray(image)
    height, width = gray.shape
    reference = _load_gray(reference_image) if reference_image else None
    if reference is not None:
        matrix, inliers = register_to_reference(reference, gray)
        if inliers < 10:
            raise ValueError("Insufficient registration inliers")
        import numpy as np
        inverse = np.linalg.inv(matrix)
        ref_height, ref_width = reference.shape
    else:
        inliers = None
        ref_height, ref_width = height, width
        if (width, height) != (
            json.loads(Path(mapping).read_text(encoding="utf-8"))["image_width"],
            json.loads(Path(mapping).read_text(encoding="utf-8"))["image_height"],
        ):
            raise ValueError("Scan dimensions differ; supply --reference-image")
    candidates = detect_candidates(gray)
    if reference is not None:
        transformed = cv2.perspectiveTransform(
            np.float32([[c.x, c.y] for c in candidates]).reshape(-1, 1, 2),
            matrix).reshape(-1, 2)
        candidates = [Candidate(float(x), float(y), c.radius)
                      for (x, y), c in zip(transformed, candidates)]
    confirmed, unresolved, ambiguous = match_globals(
        fields, candidates, ref_width, ref_height, tolerance_px)
    proposed = {}
    for name, (candidate, distance) in confirmed.items():
        if reference is not None:
            coords = cv2.perspectiveTransform(
                np.float32([[[candidate.x, candidate.y]]]), inverse)[0, 0]
            x, y = float(coords[0]), float(coords[1])
        else:
            x, y = candidate.x, candidate.y
        if 0 <= x <= width and 0 <= y <= height:
            proposed[name] = ScanPoint(x / width, y / height)
        else:
            unresolved.append(name)
    unresolved = sorted(set(unresolved))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    preview = cv2.imread(str(image))
    for name in GLOBAL_FIELDS:
        if name in proposed:
            p = proposed[name]
            x, y = round(p.x * width), round(p.y * height)
            color = (0, 170, 0)
        else:
            if reference is not None:
                px, py = points[name].x * ref_width, points[name].y * ref_height
                coords = cv2.perspectiveTransform(
                    np.float32([[[px, py]]]), inverse)[0, 0]
                x, y = round(float(coords[0])), round(float(coords[1]))
            else:
                x = round(points[name].x * width)
                y = round(points[name].y * height)
            color = (0, 0, 255)
        cv2.circle(preview, (x, y), 9, color, 2)
        cv2.putText(preview, name, (x + 12, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, .35, color, 1)
    if not cv2.imwrite(str(output_dir / "globals-overlay.png"), preview):
        raise OSError("Unable to save overlay")
    report = {
        "status": "review_required", "approved": False,
        "reference_mapping": str(mapping), "source_image": str(image),
        "registration_inliers": inliers,
        "expected_globals": len(GLOBAL_FIELDS),
        "detected_globals": len(proposed),
        "unresolved": unresolved, "ambiguous": ambiguous,
        "candidate_count": len(candidates),
        "tolerance_px": tolerance_px,
        "matches": {
            name: {"x": proposed[name].x, "y": proposed[name].y,
                   "distance_px": round(confirmed[name][1], 3)}
            for name in sorted(proposed)
        },
        "note": "Candidate matching is provisional; printed Days boxes may not be circular.",
    }
    (output_dir / "globals-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # Partial proposals are diagnostic only, never masquerade as a full mapping.
    if len(proposed) == len(GLOBAL_FIELDS) and not unresolved:
        save_mapping(output_dir / "globals-proposed.json", proposed, width, height)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Detect global fields; review required")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reference-image", type=Path)
    parser.add_argument("--tolerance-px", type=float, default=12)
    args = parser.parse_args(argv)
    report = run(args.image, args.mapping, args.output_dir,
                 args.reference_image, args.tolerance_px)
    print(json.dumps(report, indent=2))
    return 0 if not report["unresolved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
