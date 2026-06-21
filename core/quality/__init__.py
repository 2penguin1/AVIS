"""Image quality gate. Quantifies blur / exposure / resolution and decides whether the
image is good enough to judge. Abstaining on unusable images is a feature: it prevents
confident-but-wrong outputs under bad conditions. Uses numpy + Pillow only.
"""

from __future__ import annotations

from pydantic import BaseModel


class QualityReport(BaseModel):
    ok: bool
    reason: str
    blur: float
    brightness: float
    min_side: int


def assess(
    image_path: str,
    *,
    min_side: int = 64,
    blur_threshold: float = 12.0,
    dark: float = 15.0,
    bright: float = 245.0,
) -> QualityReport:
    import numpy as np
    from PIL import Image

    gray = Image.open(image_path).convert("L")
    w, h = gray.size
    side = min(w, h)
    arr = np.asarray(gray, dtype="float64")

    brightness = float(arr.mean())
    # variance of a discrete Laplacian = sharpness proxy (low => blurry/featureless)
    lap = (
        -4.0 * arr
        + np.roll(arr, 1, 0)
        + np.roll(arr, -1, 0)
        + np.roll(arr, 1, 1)
        + np.roll(arr, -1, 1)
    )
    blur = float(lap[1:-1, 1:-1].var()) if side > 2 else 0.0

    if side < min_side:
        return QualityReport(
            ok=False,
            reason="resolution too low",
            blur=blur,
            brightness=brightness,
            min_side=side,
        )
    if brightness < dark:
        return QualityReport(
            ok=False, reason="too dark", blur=blur, brightness=brightness, min_side=side
        )
    if brightness > bright:
        return QualityReport(
            ok=False,
            reason="overexposed",
            blur=blur,
            brightness=brightness,
            min_side=side,
        )
    if blur < blur_threshold:
        return QualityReport(
            ok=False,
            reason="too blurry / no detail",
            blur=blur,
            brightness=brightness,
            min_side=side,
        )
    return QualityReport(
        ok=True, reason="ok", blur=blur, brightness=brightness, min_side=side
    )
