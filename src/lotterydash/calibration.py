"""Scan-space coordinate mappings. Physical printer calibration is intentionally separate."""
from dataclasses import dataclass, asdict
from pathlib import Path
import json

SCAN_WIDTH = 1487
SCAN_HEIGHT = 2047
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ScanPoint:
    x: float
    y: float

    def __post_init__(self):
        if not (0 <= self.x <= 1 and 0 <= self.y <= 1):
            raise ValueError("Normalized scan coordinates must be between 0 and 1")


def normalize(x: float, y: float, width: int, height: int) -> ScanPoint:
    if width <= 0 or height <= 0:
        raise ValueError("Scan dimensions must be positive")
    return ScanPoint(x / width, y / height)


def to_pixels(point: ScanPoint, width: int, height: int) -> tuple[float, float]:
    if width <= 0 or height <= 0:
        raise ValueError("Scan dimensions must be positive")
    return point.x * width, point.y * height


def save_mapping(path: str | Path, points: dict[str, ScanPoint], image_width: int, image_height: int):
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Invalid image dimensions")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "image_width": image_width,
        "image_height": image_height,
        "physical_dimensions_verified": False,
        "points": {name: asdict(point) for name, point in sorted(points.items())},
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_mapping(path: str | Path) -> dict[str, ScanPoint]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported mapping schema")
    if not isinstance(data.get("points"), dict):
        raise ValueError("Invalid mapping points")
    return {name: ScanPoint(**coords) for name, coords in data["points"].items()}
