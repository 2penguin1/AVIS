"""Traffic-light state via HSV colour analysis."""

from __future__ import annotations

import numpy as np
from PIL import Image

from core.detect import classify_lights
from core.schemas import BBox, EvidenceGraph, Light, LightState


def _light_image(path, color: tuple[int, int, int]) -> str:
    arr = np.zeros((60, 60, 3), dtype="uint8")
    arr[10:50, 10:50] = color
    Image.fromarray(arr).save(path)
    return str(path)


def test_red_light_classified(tmp_path) -> None:
    p = _light_image(tmp_path / "r.png", (255, 0, 0))
    g = EvidenceGraph(
        image_id="i",
        lights=[Light(id="tl", bbox=BBox(x1=10, y1=10, x2=50, y2=50), confidence=0.9)],
    )
    classify_lights(g, p)
    assert g.lights[0].state == LightState.red


def test_green_light_classified(tmp_path) -> None:
    p = _light_image(tmp_path / "g.png", (0, 255, 0))
    g = EvidenceGraph(
        image_id="i",
        lights=[Light(id="tl", bbox=BBox(x1=10, y1=10, x2=50, y2=50), confidence=0.9)],
    )
    classify_lights(g, p)
    assert g.lights[0].state == LightState.green
