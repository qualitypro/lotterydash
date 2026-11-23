"""Sprint 04C: targeted image-template recovery for problematic boxed fields.

Uses a crop of the verified Panel A field as visual evidence, searches near
the discovered panel offset, and refuses low-confidence or ambiguous matches.
This is not OCR and does not infer unseen semantic fields.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Recovery:
    x: float
    y: float
    score: float
    margin: float


def recover_box(gray, source_x, source_y, expected_x, expected_y,
                *, template_half=14, search_radius=16,
                min_score=.65, min_margin=.025):
    """Return a visually corroborated center, or None.

    Input is a grayscale numpy array. The reference patch is centered at
    the *original mapped* field, so the recovered coordinate retains that
    semantic anchor. The output is a proposal, never automatically approved.
    """
    import cv2
    height, width = gray.shape[:2]
    sx, sy = round(source_x), round(source_y)
    ex, ey = round(expected_x), round(expected_y)
    half = template_half
    if half < 5 or search_radius < 1:
        raise ValueError("Invalid recovery window")
    if not (half <= sx < width-half and half <= sy < height-half):
        return None
    if not (half+search_radius <= ex < width-half-search_radius and
            half+search_radius <= ey < height-half-search_radius):
        return None
    template = gray[sy-half:sy+half+1, sx-half:sx+half+1]
    area = gray[ey-half-search_radius:ey+half+search_radius+1,
                ex-half-search_radius:ex+half+search_radius+1]
    if template.std() < 8:
        return None
    scores = cv2.matchTemplate(area, template, cv2.TM_CCOEFF_NORMED)
    _, maximum, _, location = cv2.minMaxLoc(scores)
    # Suppress a 5-pixel neighborhood around the winner to measure whether
    # a second distinct alignment is nearly as plausible.
    alternate = scores.copy()
    lx, ly = location
    alternate[max(0, ly-5):ly+6, max(0, lx-5):lx+6] = -1
    _, runner_up, _, _ = cv2.minMaxLoc(alternate)
    margin = float(maximum - runner_up)
    if not math.isfinite(maximum) or maximum < min_score or margin < min_margin:
        return None
    x = ex + lx - search_radius
    y = ey + ly - search_radius
    return Recovery(float(x), float(y), float(maximum), margin)


def recover_exceptions(gray, fields, panels, width, height,
                       *, min_score=.65, min_margin=.025):
    """Recover only known boxed exceptions that failed candidate matching.

    Returns per-panel recovery proposals and a list of unresolved identifiers.
    """
    boxed = {"a.draw-time.mid", "a.num.VOID"}
    recovered, unresolved = {}, []
    for panel_name, panel in panels.items():
        for field in sorted((set(panel["missing"]) | set(panel["ambiguous"])) & boxed):
            source = fields[field]
            sx, sy = source.x * width, source.y * height
            result = recover_box(
                gray, sx, sy, sx + panel["dx"], sy + panel["dy"],
                min_score=min_score, min_margin=min_margin)
            key = panel_name.lower() + field[1:]
            if result is None:
                unresolved.append(key)
            else:
                recovered[key] = result
    return recovered, unresolved
