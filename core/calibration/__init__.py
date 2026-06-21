"""Per-camera calibration: zone polygons (stop-line, no-parking, lane) loaded from
``configs/<camera_id>.json``. Used by the Tier-C rules. No calibration => no zones =>
those rules simply don't fire (the system degrades to Tier-A only).
"""

from __future__ import annotations

import json
import os

from core.schemas import Zone

CONFIG_DIR = "configs"


def load_zones(camera_id: str | None) -> list[Zone]:
    if not camera_id:
        return []
    path = os.path.join(CONFIG_DIR, f"{camera_id}.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    zones: list[Zone] = []
    for z in data.get("zones", []):
        zones.append(
            Zone(
                id=z.get("id", z["kind"]),
                kind=z["kind"],
                polygon=[(float(p[0]), float(p[1])) for p in z["polygon"]],
                direction=z.get("direction"),
            )
        )
    return zones


def point_in_polygon(
    point: tuple[float, float], polygon: list[tuple[float, float]]
) -> bool:
    """Ray-casting test. Pure Python so the rules need no geometry dependency."""
    x, y = point
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside
