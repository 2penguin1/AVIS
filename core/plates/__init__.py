"""License-plate recognition. fast-alpr (ONNX, CPU-fast) does detection + OCR; we
normalise/validate the read against the Indian plate format.

fast-alpr is heavy and optional: the default NullPlateRecognizer returns nothing, so
the pipeline and unit tests run without it. Set PLATE_PROVIDER=fastalpr to enable.
"""

from __future__ import annotations

import re
from typing import Protocol

from core.config import Settings, get_settings
from core.schemas import BBox, Plate

# Indian plate: <state 2 alpha><RTO 1-2 digit><series 1-2 alpha><number 4 digit>
INDIAN_PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$")


def normalize_plate(raw: str) -> tuple[str, bool]:
    """Uppercase + strip non-alphanumerics; return (cleaned, indian_format_ok)."""
    cleaned = re.sub(r"[^A-Z0-9]", "", raw.upper())
    return cleaned, bool(INDIAN_PLATE_RE.match(cleaned))


def _as_conf(raw: object) -> float:
    """fast-alpr may return per-char confidences as a list; collapse to a mean."""
    if isinstance(raw, (list, tuple)):
        vals = [float(v) for v in raw if isinstance(v, (int, float))]
        return sum(vals) / len(vals) if vals else 0.0
    try:
        return float(raw or 0.0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


class PlateRecognizer(Protocol):
    def read_all(self, image_path: str) -> list[Plate]: ...


class NullPlateRecognizer:
    """Default: plate recognition disabled."""

    def read_all(self, image_path: str) -> list[Plate]:
        return []


class FastAlprRecognizer:
    def __init__(self, detector_model: str, ocr_model: str) -> None:
        self._detector_model = detector_model
        self._ocr_model = ocr_model
        self._alpr = None

    def _load(self):  # noqa: ANN202
        if self._alpr is None:
            from fast_alpr import ALPR  # heavy, lazy

            self._alpr = ALPR(
                detector_model=self._detector_model, ocr_model=self._ocr_model
            )
        return self._alpr

    def read_all(self, image_path: str) -> list[Plate]:
        try:
            results = self._load().predict(image_path)
        except Exception:
            return []  # missing model / runtime error -> no plate, degrade gracefully
        plates: list[Plate] = []
        for r in results:
            ocr = getattr(r, "ocr", None)
            text = getattr(ocr, "text", "") or ""
            conf = _as_conf(getattr(ocr, "confidence", 0.0))
            cleaned, ok = normalize_plate(text)
            bbox: BBox | None = None
            box = getattr(getattr(r, "detection", None), "bounding_box", None)
            if box is not None:
                try:
                    bbox = BBox(
                        x1=float(box.x1),
                        y1=float(box.y1),
                        x2=float(box.x2),
                        y2=float(box.y2),
                    )
                except Exception:
                    bbox = None
            plates.append(Plate(text=cleaned, regex_ok=ok, confidence=conf, bbox=bbox))
        return plates


_PLATE_PROMPT = (
    "Read every vehicle license/number plate visible in this traffic image. "
    "Reply with ONLY JSON: "
    '{"plates": [{"text": "<plate as written>", "box": [x1,y1,x2,y2]}]} '
    "where box is the plate's pixel bounding box; use [] if no plate is legible."
)


class GeminiPlateRecognizer:
    """Reads plates with the Gemini vision model — a fallback when fast-alpr reads
    nothing. Any error returns no plate (graceful degradation). Costs Gemini quota.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

    def _client_obj(self):  # noqa: ANN202
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def read_all(self, image_path: str) -> list[Plate]:
        import json
        import sys
        from io import BytesIO

        from core.llm import call_with_retry

        try:
            from google.genai import types
            from PIL import Image

            buf = BytesIO()
            Image.open(image_path).convert("RGB").save(buf, format="JPEG")
            resp = call_with_retry(
                lambda: self._client_obj().models.generate_content(
                    model=self._model,
                    contents=[
                        _PLATE_PROMPT,
                        types.Part.from_bytes(
                            data=buf.getvalue(), mime_type="image/jpeg"
                        ),
                    ],
                ),
                attempts=2,
                base_delay=3.0,
            )
            text = (resp.text or "").strip().removeprefix("```json").removeprefix("```")
            data = json.loads(text.removesuffix("```").strip())
        except Exception as e:  # noqa: BLE001
            print(f"[gemini.plate] {type(e).__name__}: {e}", file=sys.stderr)
            return []

        plates: list[Plate] = []
        for item in data.get("plates", []):
            cleaned, ok = normalize_plate(str(item.get("text", "")))
            if not cleaned:
                continue
            bbox: BBox | None = None
            box = item.get("box")
            if isinstance(box, (list, tuple)) and len(box) == 4:
                try:
                    bbox = BBox(
                        x1=float(box[0]),
                        y1=float(box[1]),
                        x2=float(box[2]),
                        y2=float(box[3]),
                    )
                except (TypeError, ValueError):
                    bbox = None
            plates.append(Plate(text=cleaned, regex_ok=ok, confidence=0.6, bbox=bbox))
        return plates


class ChainPlateRecognizer:
    """Try fast-alpr first (free, local); fall back to Gemini only when empty,
    so the quota is spent sparingly."""

    def __init__(self, primary: PlateRecognizer, fallback: PlateRecognizer) -> None:
        self._primary = primary
        self._fallback = fallback

    def read_all(self, image_path: str) -> list[Plate]:
        plates = self._primary.read_all(image_path)
        if any(p.text for p in plates):
            return plates
        return self._fallback.read_all(image_path)


def get_plate_recognizer(settings: Settings | None = None) -> PlateRecognizer:
    settings = settings or get_settings()
    has_gemini = settings.llm_provider == "gemini" and bool(settings.gemini_api_key)
    if settings.plate_provider == "fastalpr":
        alpr = FastAlprRecognizer(
            settings.plate_detector_model, settings.plate_ocr_model
        )
        if has_gemini:
            return ChainPlateRecognizer(
                alpr,
                GeminiPlateRecognizer(settings.gemini_api_key, settings.gemini_model),
            )
        return alpr
    if settings.plate_provider == "gemini" and has_gemini:
        return GeminiPlateRecognizer(settings.gemini_api_key, settings.gemini_model)
    return NullPlateRecognizer()
