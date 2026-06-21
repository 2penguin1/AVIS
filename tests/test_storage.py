"""Read-only checks for the interpretability storage helpers (no writes)."""

from __future__ import annotations

from core import storage


def test_get_violation_unknown_returns_none() -> None:
    storage.init_db()
    assert storage.get_violation("does_not_exist") is None


def test_image_dims_unknown_returns_none() -> None:
    storage.init_db()
    assert storage.image_dims("does_not_exist") is None
