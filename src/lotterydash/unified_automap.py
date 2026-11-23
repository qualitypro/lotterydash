"""Sprint 04I: unified, review-only full-slip AutoMap orchestration.

Runs the independent panel and global detectors and merges only complete,
non-overlapping results. No printing, approval, or source-file modification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .automap import _cv
from .calibration import load_mapping, save_mapping
from .full_slip_automap import run as detect_panels
from .global_detector import run as detect_globals
from .global_options import GLOBAL_FIELDS, mapping_summary


def combine_proposals(panel_points, global_points):
    """Require exactly the expected semantic IDs; reject duplicate IDs."""
    overlap = set(panel_points) & set(global_points)
    if overlap:
        raise ValueError(f"Duplicate field IDs: {sorted(overlap)}")
    merged = {**panel_points, **global_points}
    summary = mapping_summary(merged)
    expected_panels = {f"{panel}.{suffix}" for panel in "abcde"
                       for suffix in (key[2:] for key in panel_points
                                      if key.startswith("a."))}
    if (not summary["complete"] or set(merged) !=
            expected_panels | set(GLOBAL_FIELDS)):
        raise ValueError("Incomplete or inconsistent 231-field proposal")
    return merged


def run(image, panel_mapping, global_mapping, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    panels_dir = output / "panels"
    globals_dir = output / "globals"
    panel_report = detect_panels(image, panel_mapping, panels_dir)
    global_report = detect_globals(image, global_mapping, globals_dir)
    panel_ok = bool(panel_report["complete_detection"])
    global_ok = (global_report["detected_globals"] == len(GLOBAL_FIELDS)
                 and not global_report["unresolved"]
                 and not global_report["ambiguous"])
    merged = None
    if panel_ok and global_ok:
        panel_points = load_mapping(panels_dir / "full-slip-proposed.json")
        global_points = load_mapping(globals_dir / "globals-proposed.json")
        merged = combine_proposals(panel_points, global_points)
    cv2 = _cv()
    canvas = cv2.imread(str(image))
    if canvas is None:
        raise ValueError(f"Cannot read scan: {image}")
    height, width = canvas.shape[:2]
    if merged is not None:
        for name, point in merged.items():
            x, y = round(point.x * width), round(point.y * height)
            color = (0, 180, 0) if name.startswith("global.") else (255, 170, 0)
            cv2.circle(canvas, (x, y), 6, color, 2)
        save_mapping(output / "automap-231-proposed.json", merged, width, height)
    else:
        # Overlay partial detections for review, without inventing missing fields.
        for part, filename in ((panels_dir, "full-slip-proposed.json"),
                               (globals_dir, "globals-proposed.json")):
            path = part / filename
            if path.exists():
                for name, point in load_mapping(path).items():
                    x, y = round(point.x * width), round(point.y * height)
                    cv2.circle(canvas, (x, y), 6, (0, 170, 255), 2)
    if not cv2.imwrite(str(output / "automap-231-overlay.png"), canvas):
        raise OSError("Cannot save unified overlay")
    report = {
        "status": "review_required", "approved": False,
        "source_image": str(image),
        "complete_detection": merged is not None,
        "panel_detection_complete": panel_ok,
        "global_detection_complete": global_ok,
        "detected_fields": len(merged) if merged is not None else
            panel_report["matched_fields"] + global_report["detected_globals"],
        "expected_fields": 231,
        "panel_report": str(panels_dir / "full-slip-report.json"),
        "global_report": str(globals_dir / "globals-report.json"),
        "overlay": str(output / "automap-231-overlay.png"),
        "proposed_mapping": str(output / "automap-231-proposed.json")
            if merged is not None else None,
        "note": "Detection completeness is not print alignment or visual approval.",
    }
    (output / "automap-231-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Unified review-only 231-field AutoMap")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--panel-mapping", type=Path, required=True)
    parser.add_argument("--global-mapping", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run(args.image, args.panel_mapping, args.global_mapping, args.output_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["complete_detection"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
