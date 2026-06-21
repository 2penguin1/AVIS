"""FastAPI surface: upload, status, violations, review queue, analytics. Routes only —
all real work goes through ``core``. Heavy processing runs in a background task.
"""

from __future__ import annotations

import os

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import queue, storage
from core.config import get_settings
from core.schemas import ImageMeta

settings = get_settings()
app = FastAPI(title="AVIS — Automated Violation Intelligence System")


class ReviewIn(BaseModel):
    decision: str  # approved | rejected
    reviewer: str | None = None
    note: str | None = None


@app.on_event("startup")
def _startup() -> None:
    storage.init_db()


@app.post("/images")
async def upload_image(
    background: BackgroundTasks, file: UploadFile, camera_id: str | None = None
) -> dict:
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "Upload must be an image.")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file.")
    meta = ImageMeta(filename=file.filename or "upload.jpg", camera_id=camera_id)
    storage.save_image(meta)
    storage.save_upload(meta.id, meta.filename, data)
    background.add_task(queue.run, meta.id)
    return {"image_id": meta.id, "status": meta.status.value}


@app.get("/images/{image_id}")
def get_image(image_id: str) -> dict:
    row = storage.get_image(image_id)
    if row is None:
        raise HTTPException(404, "Unknown image.")
    dims = storage.image_dims(image_id) or {}
    return {
        "image_id": row.id,
        "status": row.status,
        "annotated_url": f"/files/{image_id}_annotated.jpg",
        "width": dims.get("width"),
        "height": dims.get("height"),
        "violations": storage.violations_for(image_id),
    }


@app.get("/violations")
def list_violations(
    limit: int = 200,
    type: str | None = None,
    route: str | None = None,
    review_status: str | None = None,
    plate: str | None = None,
) -> list[dict]:
    return storage.list_violations(
        limit=limit, type=type, route=route, review_status=review_status, plate=plate
    )


@app.get("/violations/{violation_id}")
def get_violation(violation_id: str) -> dict:
    """Full single-violation payload for the interpretable detail view."""
    v = storage.get_violation(violation_id)
    if v is None:
        raise HTTPException(404, "Unknown violation.")
    return v


@app.get("/review-queue")
def review_queue(limit: int = 200) -> list[dict]:
    return storage.review_queue(limit)


@app.post("/violations/{violation_id}/review")
def review_violation(violation_id: str, body: ReviewIn) -> dict:
    if body.decision not in {"approved", "rejected"}:
        raise HTTPException(400, "decision must be 'approved' or 'rejected'.")
    updated = storage.review(violation_id, body.decision, body.reviewer, body.note)
    if updated is None:
        raise HTTPException(404, "Unknown violation.")
    return updated


@app.get("/analytics")
def analytics() -> dict:
    return storage.analytics()


@app.get("/analytics/summary")
def analytics_summary() -> dict[str, int]:
    return storage.summary()


@app.get("/runtime")
def runtime() -> dict[str, object]:
    return {
        "plate_ocr_enabled": settings.plate_provider != "null",
        "plate_provider": settings.plate_provider,
        "llm_provider": settings.llm_provider,
        "vlm_enabled": settings.llm_provider == "gemini"
        and bool(settings.gemini_api_key),
        "auto_confirm_threshold": settings.auto_confirm_threshold,
        "review_threshold": settings.review_threshold,
    }


@app.get("/files/{name}")
def get_file(name: str) -> FileResponse:
    path = os.path.join(settings.image_dir, name)
    if not os.path.exists(path):
        raise HTTPException(404, "Not found.")
    return FileResponse(path)


# Static dashboard (mounted last so it doesn't shadow the API routes).
# Prefer the built React app (frontend/dist); fall back to the source folder.
_root = os.path.dirname(os.path.dirname(__file__))
_dist = os.path.join(_root, "frontend", "dist")
_frontend = _dist if os.path.isdir(_dist) else os.path.join(_root, "frontend")
if os.path.isdir(_frontend):
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
