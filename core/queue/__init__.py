"""Background processing. MVP runs in-process (FastAPI BackgroundTasks). To scale,
swap ``run`` to enqueue onto Celery/RQ (Redis) — callers stay unchanged.

This layer is the seam between pure pipeline logic and side effects (storage + files):
quality gate -> preprocess -> pipeline -> hash + annotate + persist. Detection runs on
the enhanced image; evidence (hash + annotation) uses the untouched original.
"""

from __future__ import annotations

from core import evidence, preprocess, quality, storage
from core.config import get_settings
from core.pipeline import process
from core.schemas import ImageStatus


def process_and_store(image_id: str) -> None:
    row = storage.get_image(image_id)
    path = storage.original_path(image_id)
    if path is None:
        return
    settings = get_settings()
    storage.set_status(image_id, ImageStatus.processing)
    try:
        report = quality.assess(
            path,
            min_side=settings.quality_min_side,
            blur_threshold=settings.quality_blur_threshold,
            dark=settings.quality_dark_threshold,
            bright=settings.quality_bright_threshold,
        )
        if not report.ok:
            # Abstain: an unusable image yields no determination, not a false positive.
            storage.set_status(image_id, ImageStatus.undeterminable)
            return

        enhanced = preprocess.enhance(path)
        try:
            camera_id = row.camera_id if row else None
            violations, graph = process(image_id, enhanced, camera_id=camera_id)
        finally:
            preprocess.cleanup(enhanced, path)

        digest = "sha256:" + evidence.hash_image(path)
        out = storage.annotated_path(image_id)
        evidence.annotate(path, out, violations, graph)
        url = f"/files/{image_id}_annotated.jpg"
        for v in violations:
            v.evidence_hash = digest
            v.annotated_url = url
            storage.add_violation(v)
        storage.set_status(image_id, ImageStatus.completed)
    except Exception:
        storage.set_status(image_id, ImageStatus.failed)
        raise


def run(image_id: str) -> None:
    """Entry point used by the API's BackgroundTasks (or a future Celery task)."""
    process_and_store(image_id)
