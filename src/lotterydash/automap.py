"""Template-guided playslip AutoMap.

Detect bubble centers in a new scan and associate them with known semantic field
IDs. Source mappings are read-only. A new slip layout needs human review.
OpenCV is optional and imported only when AutoMap is invoked.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .calibration import ScanPoint, load_mapping, save_mapping


@dataclass(frozen=True)
class Candidate:
    x: float
    y: float
    radius: float


def _cv():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("AutoMap requires OpenCV: pip install opencv-python-headless") from exc
    return cv2


def _load_gray(path):
    cv2 = _cv()
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Cannot read image: {path}")
    return image


def register_to_reference(reference, target):
    """Return image-to-reference homography and inlier count, or raise."""
    cv2 = _cv()
    orb = cv2.ORB_create(nfeatures=4000)
    kp_ref, desc_ref = orb.detectAndCompute(reference, None)
    kp_new, desc_new = orb.detectAndCompute(target, None)
    if desc_ref is None or desc_new is None:
        raise ValueError("Insufficient image features for registration")
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(desc_new, desc_ref, k=2)
    good = [a for pair in pairs if len(pair) == 2 for a, b in [pair] if a.distance < .72 * b.distance]
    if len(good) < 12:
        raise ValueError("Insufficient reliable matches; rescan with full slip visible")
    import numpy as np
    src = np.float32([kp_new[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    inliers = int(mask.sum()) if mask is not None else 0
    if matrix is None or inliers < 10:
        raise ValueError("Perspective registration failed")
    return matrix, inliers


def detect_candidates(gray, min_radius=4, max_radius=32):
    """Detect approximately circular printed outlines, de-duplicating centers."""
    cv2 = _cv()
    if min_radius < 1 or max_radius <= min_radius:
        raise ValueError("Invalid bubble radius range")
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    binary = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 31, 8
    )
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    found = []
    for contour in contours:
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if area <= 0 or perimeter <= 0:
            continue
        (x, y), radius = cv2.minEnclosingCircle(contour)
        if not min_radius <= radius <= max_radius:
            continue
        circularity = 4 * 3.141592653589793 * area / (perimeter * perimeter)
        if circularity < .58:
            continue
        found.append(Candidate(float(x), float(y), float(radius)))
    found.sort(key=lambda c: (c.y, c.x, c.radius))
    unique = []
    for candidate in found:
        if not any((candidate.x - c.x) ** 2 + (candidate.y - c.y) ** 2 <
                   (min(candidate.radius, c.radius) * .8) ** 2 for c in unique):
            unique.append(candidate)
    return unique


def match_fields(points, candidates, width, height, tolerance_px):
    """Unique nearest-neighbor assignment; ambiguity is flagged, never guessed."""
    if tolerance_px <= 0:
        raise ValueError("tolerance_px must be positive")
    edges = []
    for field, point in points.items():
        expected_x, expected_y = point.x * width, point.y * height
        for index, candidate in enumerate(candidates):
            distance = ((candidate.x - expected_x) ** 2 +
                        (candidate.y - expected_y) ** 2) ** .5
            if distance <= tolerance_px:
                edges.append((distance, field, index))
    edges.sort()
    assigned, used = {}, set()
    for distance, field, index in edges:
        if field not in assigned and index not in used:
            assigned[field] = (candidates[index], distance)
            used.add(index)
    # Multiple close candidates are not safe to silently resolve.
    ambiguous = []
    for field, (candidate, distance) in assigned.items():
        alternatives = [d for d, f, i in edges if f == field and
                        candidates[i] != candidate and d <= distance + 2.0]
        if alternatives:
            ambiguous.append(field)
    missing = sorted(set(points) - set(assigned))
    return assigned, missing, sorted(ambiguous)


def run(image_path, mapping_path, output_dir, reference_image=None,
        tolerance_px=18, min_radius=4, max_radius=32, panel="a"):
    cv2 = _cv()
    gray = _load_gray(image_path)
    height, width = gray.shape
    mapping = load_mapping(mapping_path)
    fields = {k: v for k, v in mapping.items()
              if panel == "all" or k.lower().startswith(panel.lower() + ".")}
    if not fields:
        raise ValueError("No matching fields in reference mapping")
    candidates = detect_candidates(gray, min_radius, max_radius)
    if reference_image:
        reference = _load_gray(reference_image)
        matrix, inliers = register_to_reference(reference, gray)
        import numpy as np
        transformed = cv2.perspectiveTransform(
            np.float32([[c.x, c.y] for c in candidates]).reshape(-1, 1, 2),
            matrix
        ).reshape(-1, 2)
        candidates = [Candidate(float(x), float(y), c.radius)
                      for (x, y), c in zip(transformed, candidates)]
        ref_height, ref_width = reference.shape
        width_match, height_match = ref_width, ref_height
    else:
        inliers = None
        width_match, height_match = width, height
    assigned, missing, ambiguous = match_fields(
        fields, candidates, width_match, height_match, tolerance_px
    )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    proposed = {name: ScanPoint(c.x / width_match, c.y / height_match)
                for name, (c, _) in assigned.items()
                if 0 <= c.x <= width_match and 0 <= c.y <= height_match}
    complete = len(proposed) == len(fields) and not missing and not ambiguous
    report = {
        "status": "review_required",
        "complete_detection": complete,
        "approved": False,
        "source_image": str(image_path),
        "reference_mapping": str(mapping_path),
        "reference_image": str(reference_image) if reference_image else None,
        "registration_inliers": inliers,
        "detected_candidates": len(candidates),
        "expected_fields": len(fields),
        "matched_fields": len(proposed),
        "missing_fields": missing,
        "ambiguous_fields": ambiguous,
        "matches": {
            name: {"x": p.x, "y": p.y,
                   "distance_px": round(assigned[name][1], 3)}
            for name, p in sorted(proposed.items())
        },
    }
    (output_dir / "automap-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    # Preview always uses reference image coordinates when registration is used.
    preview = cv2.imread(str(reference_image or image_path))
    for name, p in proposed.items():
        x, y = round(p.x * width_match), round(p.y * height_match)
        cv2.circle(preview, (x, y), 7, (0, 180, 0), 2)
        cv2.putText(preview, name, (x + 9, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, .35, (0, 120, 0), 1)
    for name in missing:
        p = fields[name]
        cv2.circle(preview, (round(p.x * width_match), round(p.y * height_match)),
                   9, (0, 0, 255), 2)
    cv2.imwrite(str(output_dir / "automap-overlay.png"), preview)
    # Never overwrite the user's authoritative mapping, even on full detection.
    if complete:
        save_mapping(output_dir / "automap-proposed.json",
                     proposed, width_match, height_match)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Detect and propose playslip bubble mappings; never overwrites originals")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, default=Path("maps/pick3-mapping.json"))
    parser.add_argument("--reference-image", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("images/diagnostics/automap"))
    parser.add_argument("--tolerance-px", type=float, default=18)
    parser.add_argument("--min-radius", type=int, default=4)
    parser.add_argument("--max-radius", type=int, default=32)
    parser.add_argument("--panel", default="a")
    args = parser.parse_args(argv)
    report = run(args.image, args.mapping, args.output_dir, args.reference_image,
                 args.tolerance_px, args.min_radius, args.max_radius, args.panel)
    print(json.dumps({k: v for k, v in report.items() if k != "matches"}, indent=2))
    print(f"Review overlay and report in {args.output_dir}")
    return 0 if report["complete_detection"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
