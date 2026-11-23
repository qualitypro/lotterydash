"""Versioned, non-destructive production mapping publication.

A published mapping is a snapshot, never the editable draft. This module does
not print or assert that a mapping is physically calibrated.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .calibration import load_mapping
from .global_options import mapping_summary

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")


def validate_for_game(game: str, mapping: Path) -> dict:
    points = load_mapping(mapping)
    if game == "pick3":
        summary = mapping_summary(points)
        if not summary["complete"]:
            raise ValueError("Pick 3 production mapping requires all 231 fields")
        return summary
    raise ValueError(
        f"Production field validation is not implemented for {game}; "
        "publication is blocked until a game-specific schema is defined")


def publish_mapping(project: dict, mapping: Path, output_root: Path,
                    *, reviewed: bool, calibration_verified: bool = False) -> dict:
    """Publish a validated snapshot only after explicit review.

    Never overwrite an existing production version. The returned metadata can
    be recorded in the project by the caller after a successful publication.
    """
    if not reviewed:
        raise ValueError("Explicit visual review is required before publication")
    game = project.get("game")
    summary = validate_for_game(game, Path(mapping))
    project_id = project.get("project_id")
    if not isinstance(project_id, str) or not _SAFE_ID.fullmatch(project_id):
        raise ValueError("Project must have a safe, stable project_id")
    source = Path(mapping)
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    root = Path(output_root) / project_id / "production"
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    version = f"{timestamp}-{digest[:12]}"
    destination = root / f"{version}.mapping.json"
    metadata = root / f"{version}.review.json"
    with destination.open("xb") as handle:
        handle.write(data)
    record = {
        "version": version,
        "game": game,
        "project_id": project_id,
        "mapping_file": destination.name,
        "sha256": digest,
        "field_count": len(load_mapping(destination)),
        "reviewed": True,
        "calibration_verified": bool(calibration_verified),
        "production_mapping": True,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
    }
    try:
        with metadata.open("x", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2)
            handle.write("\n")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return record


def verify_published_mapping(root: Path, project_id: str, version: str) -> dict:
    if not _SAFE_ID.fullmatch(project_id) or not _SAFE_ID.fullmatch(version):
        raise ValueError("Invalid project or version")
    directory = Path(root) / project_id / "production"
    record = json.loads((directory / f"{version}.review.json").read_text(encoding="utf-8"))
    if record.get("project_id") != project_id or record.get("version") != version:
        raise ValueError("Production metadata does not match requested version")
    mapping = directory / record["mapping_file"]
    if mapping.name != f"{version}.mapping.json":
        raise ValueError("Invalid mapping filename")
    if hashlib.sha256(mapping.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError("Production mapping integrity check failed")
    validate_for_game(record["game"], mapping)
    return record
