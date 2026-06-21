"""Quality gate: pass detailed images, abstain on unusable ones."""

from __future__ import annotations

import numpy as np
from PIL import Image

from core.quality import assess


def _save(arr: np.ndarray, path) -> str:
    Image.fromarray(arr.astype("uint8")).save(path)
    return str(path)


def test_good_image_passes(tmp_path) -> None:
    rng = np.random.default_rng(0)
    arr = rng.integers(0, 255, size=(120, 120, 3))
    report = assess(_save(arr, tmp_path / "g.png"))
    assert report.ok


def test_dark_image_abstains(tmp_path) -> None:
    arr = np.zeros((120, 120, 3))
    report = assess(_save(arr, tmp_path / "d.png"))
    assert not report.ok
    assert report.reason == "too dark"


def test_low_resolution_abstains(tmp_path) -> None:
    rng = np.random.default_rng(1)
    arr = rng.integers(0, 255, size=(20, 20, 3))
    report = assess(_save(arr, tmp_path / "s.png"))
    assert not report.ok
    assert report.reason == "resolution too low"


def test_flat_image_abstains(tmp_path) -> None:
    arr = np.full((120, 120, 3), 128)
    report = assess(_save(arr, tmp_path / "f.png"))
    assert not report.ok  # no detail -> blur score ~0
