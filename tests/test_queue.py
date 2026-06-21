"""Queue integration: quality thresholds should be configurable from settings."""

from __future__ import annotations

from pathlib import Path

from core import queue
from core.config import Settings
from core.schemas import ImageMeta, ImageStatus


def test_process_and_store_respects_quality_threshold_settings(
    monkeypatch, tmp_path: Path
) -> None:
    image = tmp_path / "sample.jpg"
    image.write_bytes(b"fake")
    meta = ImageMeta(id="img_cfg", filename="sample.jpg")
    statuses: list[ImageStatus] = []

    monkeypatch.setattr(queue.storage, "get_image", lambda image_id: meta)
    monkeypatch.setattr(queue.storage, "original_path", lambda image_id: str(image))
    monkeypatch.setattr(
        queue.storage, "set_status", lambda image_id, status: statuses.append(status)
    )

    assessed: dict[str, float] = {}

    class _Report:
        ok = False

    def fake_assess(
        path: str, *, min_side: int, blur_threshold: float, dark: float, bright: float
    ):
        assessed.update(
            {
                "min_side": min_side,
                "blur_threshold": blur_threshold,
                "dark": dark,
                "bright": bright,
            }
        )
        return _Report()

    monkeypatch.setattr(queue.quality, "assess", fake_assess)
    monkeypatch.setattr(
        queue,
        "get_settings",
        lambda: Settings(
            quality_min_side=80,
            quality_blur_threshold=7.5,
            quality_dark_threshold=10.0,
            quality_bright_threshold=250.0,
        ),
    )

    queue.process_and_store("img_cfg")

    assert assessed == {
        "min_side": 80,
        "blur_threshold": 7.5,
        "dark": 10.0,
        "bright": 250.0,
    }
    assert statuses == [ImageStatus.processing, ImageStatus.undeterminable]
