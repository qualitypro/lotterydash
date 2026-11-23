"""Game-based LotteryDash projects. No printer operations or implicit approval."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

GAMES = {"pick3": "Pick 3", "pick4": "Pick 4", "powerball": "Powerball"}
SCHEMA_VERSION = 1


def new_project(name: str, game: str) -> dict:
    name = name.strip()
    if not name or len(name) > 120:
        raise ValueError("Project name must be 1–120 characters")
    if game not in GAMES:
        raise ValueError("Unsupported lottery game")
    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "game": game,
        "scan": None,
        "mapping": None,
        "calibration": None,
        "plays": [],
        "global_options": {},
        "mapping_approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_project(project: dict) -> dict:
    if not isinstance(project, dict) or project.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported project schema")
    if project.get("game") not in GAMES:
        raise ValueError("Unsupported lottery game")
    if not isinstance(project.get("name"), str) or not project["name"].strip():
        raise ValueError("Invalid project name")
    if not isinstance(project.get("plays"), list):
        raise ValueError("Invalid plays")
    if not isinstance(project.get("global_options"), dict):
        raise ValueError("Invalid global options")
    if not isinstance(project.get("mapping_approved"), bool):
        raise ValueError("Invalid approval state")
    return project


def project_filename(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
    return (slug or "lottery-project") + ".lottery.json"


def save_project(path: Path, project: dict, overwrite: bool = False) -> Path:
    validate_project(project)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(project, indent=2, ensure_ascii=False) + "\n"
    if not overwrite:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(payload)
    else:
        import os
        import tempfile
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                    dir=path.parent, prefix=".lottery-", suffix=".tmp",
                    delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return path


def load_project(path: Path) -> dict:
    return validate_project(json.loads(Path(path).read_text(encoding="utf-8")))
