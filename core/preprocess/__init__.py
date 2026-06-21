"""Image enhancement for varying conditions (low light, rain, noise). Geometry is
preserved (no resize/crop) so detection boxes stay valid on the original image, which is
what we annotate and hash for evidence.

Prefers OpenCV (CLAHE + denoise + gamma); falls back to a Pillow-only path so the code
runs without cv2 installed. ``enhance`` writes to a temp file and returns its path.
"""

from __future__ import annotations

import os
import tempfile


def _enhance_cv2(src: str, dst: str) -> None:
    import cv2  # heavy, lazy
    import numpy as np

    img = cv2.imread(src)
    if img is None:
        raise ValueError("cv2 could not read image")
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    lo, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lo = clahe.apply(lo)
    img = cv2.cvtColor(cv2.merge((lo, a, b)), cv2.COLOR_LAB2BGR)
    img = cv2.fastNlMeansDenoisingColored(img, None, 5, 5, 7, 21)
    if img.mean() < 70:  # brighten dark scenes (gamma < 1)
        inv = 1.0 / 0.6
        table = ((np.arange(256) / 255.0) ** inv * 255).astype("uint8")
        img = cv2.LUT(img, table)
    cv2.imwrite(dst, img)


def _enhance_pil(src: str, dst: str) -> None:
    from PIL import Image, ImageFilter, ImageOps

    img = Image.open(src).convert("RGB")
    img = ImageOps.autocontrast(img, cutoff=1)
    img = img.filter(ImageFilter.MedianFilter(size=3))  # light denoise
    img.save(dst, format="JPEG")


def enhance(src: str) -> str:
    fd, dst = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    try:
        _enhance_cv2(src, dst)
    except Exception:
        _enhance_pil(src, dst)
    return dst


def cleanup(path: str, keep: str) -> None:
    if path != keep and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
