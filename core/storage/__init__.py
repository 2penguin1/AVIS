"""The only module that touches the database and the image store.

DB: SQLModel/SQLAlchemy — the connection URL selects SQLite (local dev default) or
Postgres (full stack). Images: local filesystem now; a MinIO/S3 backend plugs in behind
the same functions without touching callers.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, col, create_engine, select

from core.config import get_settings
from core.schemas import ImageMeta, ImageStatus, Route, Violation

_settings = get_settings()
_connect_args = (
    {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(_settings.database_url, connect_args=_connect_args)


class ImageRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    filename: str
    camera_id: str | None = None
    status: str = ImageStatus.pending.value
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ViolationRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    image_id: str = Field(index=True)
    type: str = Field(index=True)
    route: str = Field(default="", index=True)
    review_status: str = Field(default="", index=True)  # ""|pending|approved|rejected
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


def init_db() -> None:
    os.makedirs(_settings.image_dir, exist_ok=True)
    SQLModel.metadata.create_all(engine)


# --- images -------------------------------------------------------------- #
def save_image(meta: ImageMeta) -> None:
    with Session(engine) as s:
        s.add(
            ImageRow(
                id=meta.id,
                filename=meta.filename,
                camera_id=meta.camera_id,
                status=meta.status.value,
            )
        )
        s.commit()


def set_status(image_id: str, status: ImageStatus) -> None:
    with Session(engine) as s:
        row = s.get(ImageRow, image_id)
        if row is not None:
            row.status = status.value
            s.add(row)
            s.commit()


def get_image(image_id: str) -> ImageRow | None:
    with Session(engine) as s:
        return s.get(ImageRow, image_id)


def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1] or ".jpg"


def save_upload(image_id: str, filename: str, data: bytes) -> str:
    path = os.path.join(_settings.image_dir, f"{image_id}{_ext(filename)}")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def original_path(image_id: str) -> str | None:
    row = get_image(image_id)
    if row is None:
        return None
    return os.path.join(_settings.image_dir, f"{image_id}{_ext(row.filename)}")


def annotated_path(image_id: str) -> str:
    return os.path.join(_settings.image_dir, f"{image_id}_annotated.jpg")


# --- violations ---------------------------------------------------------- #
def add_violation(v: Violation) -> None:
    review_status = "pending" if v.route == Route.human_review else ""
    payload = v.model_dump(mode="json")
    payload["review_status"] = review_status
    payload["audit"] = []
    with Session(engine) as s:
        s.add(
            ViolationRow(
                id=v.id,
                image_id=v.image_id,
                type=v.type,
                route=v.route.value,
                review_status=review_status,
                payload=payload,
            )
        )
        s.commit()


def list_violations(
    limit: int = 200,
    type: str | None = None,
    route: str | None = None,
    review_status: str | None = None,
    plate: str | None = None,
) -> list[dict[str, Any]]:
    with Session(engine) as s:
        stmt = select(ViolationRow)
        if type:
            stmt = stmt.where(ViolationRow.type == type)
        if route:
            stmt = stmt.where(ViolationRow.route == route)
        if review_status:
            stmt = stmt.where(ViolationRow.review_status == review_status)
        stmt = stmt.order_by(col(ViolationRow.created_at).desc()).limit(limit)
        out = [r.payload for r in s.exec(stmt).all()]
    if plate:
        needle = plate.upper()
        out = [p for p in out if needle in ((p.get("plate") or {}).get("text") or "")]
    return out


def get_violation(violation_id: str) -> dict[str, Any] | None:
    """Full stored payload (scores, audit, sufficiency, hash) for the detail view."""
    with Session(engine) as s:
        row = s.get(ViolationRow, violation_id)
        return row.payload if row is not None else None


def image_dims(image_id: str) -> dict[str, int] | None:
    """Original image width/height (for overlay rendering). Read on demand via PIL."""
    path = original_path(image_id)
    if not path or not os.path.exists(path):
        return None
    try:
        from PIL import Image

        with Image.open(path) as im:
            w, h = im.size
        return {"width": int(w), "height": int(h)}
    except Exception:  # noqa: BLE001
        return None


def violations_for(image_id: str) -> list[dict[str, Any]]:
    with Session(engine) as s:
        rows = s.exec(
            select(ViolationRow).where(ViolationRow.image_id == image_id)
        ).all()
        return [r.payload for r in rows]


def review_queue(limit: int = 200) -> list[dict[str, Any]]:
    return list_violations(limit=limit, review_status="pending")


def review(
    violation_id: str,
    decision: str,
    reviewer: str | None = None,
    note: str | None = None,
) -> dict[str, Any] | None:
    with Session(engine) as s:
        row = s.get(ViolationRow, violation_id)
        if row is None:
            return None
        payload = dict(row.payload)
        payload["review_status"] = decision
        audit = list(payload.get("audit", []))
        audit.append(
            {
                "action": "review",
                "decision": decision,
                "reviewer": reviewer or "anonymous",
                "note": note or "",
                "ts": datetime.utcnow().isoformat(),
            }
        )
        payload["audit"] = audit
        row.review_status = decision
        row.payload = payload
        s.add(row)
        s.commit()
        return payload


def analytics() -> dict[str, Any]:
    by_type: dict[str, int] = {}
    by_route: dict[str, int] = {}
    by_day: dict[str, int] = {}
    total = 0
    pending = 0
    plates_read = 0
    plates_valid = 0
    with Session(engine) as s:
        for r in s.exec(select(ViolationRow)).all():
            by_type[r.type] = by_type.get(r.type, 0) + 1
            by_route[r.route] = by_route.get(r.route, 0) + 1
            day = r.created_at.date().isoformat()
            by_day[day] = by_day.get(day, 0) + 1
            total += 1
            if r.review_status == "pending":
                pending += 1
            plate = (r.payload or {}).get("plate")
            if plate and plate.get("text"):
                plates_read += 1
                if plate.get("regex_ok"):
                    plates_valid += 1
    return {
        "total": total,
        "pending_review": pending,
        "plate_ocr_enabled": _settings.plate_provider != "null",
        "plates_read": plates_read,
        "plates_valid": plates_valid,
        "by_type": by_type,
        "by_route": by_route,
        "by_day": dict(sorted(by_day.items())),
    }


def summary() -> dict[str, int]:
    return analytics()["by_type"]
