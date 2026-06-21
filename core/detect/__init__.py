"""Detection + attribute classifiers. Heavy libs (ultralytics) are imported lazily so
the package (and unit tests) import fine without them. Tests inject fakes via the
Detector / HelmetClassifier protocols.
"""

from __future__ import annotations

import sys
from typing import Protocol

from core.config import Settings, get_settings
from core.schemas import (
    BBox,
    Detection,
    DetectionResult,
    Edge,
    EvidenceGraph,
    Person,
    PersonRole,
    new_id,
)

# COCO classes we care about (ultralytics default model names).
_KEEP = {
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck",
    "traffic light",
}


class Detector(Protocol):
    def detect(self, image_path: str) -> DetectionResult: ...


class HelmetClassifier(Protocol):
    def apply(self, graph: EvidenceGraph, image_path: str) -> None: ...


class YoloDetector:
    """Ultralytics YOLO over the COCO classes we need."""

    def __init__(self, weights: str, conf: float = 0.25) -> None:
        self._weights = weights
        self._conf = conf
        self._model = None  # lazy

    def _load(self):  # noqa: ANN202
        if self._model is None:
            from ultralytics import YOLO  # heavy, lazy

            self._model = YOLO(self._weights)
        return self._model

    def detect(self, image_path: str) -> DetectionResult:
        model = self._load()
        result = model(image_path, conf=self._conf, verbose=False)[0]
        names = result.names
        h, w = result.orig_shape
        dets: list[Detection] = []
        for box in result.boxes:
            label = names[int(box.cls)]
            if label not in _KEEP:
                continue
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            dets.append(
                Detection(
                    label=label,
                    bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    confidence=float(box.conf),
                )
            )
        return DetectionResult(image_width=int(w), image_height=int(h), detections=dets)


class NullHelmetClassifier:
    """No helmet model configured -> leave helmet undetermined."""

    def apply(self, graph: EvidenceGraph, image_path: str) -> None:
        return None


def _helmet_verdict(label: str) -> bool | None:
    """Map a helmet-model class name to a verdict. None = rider present, helmet unknown.

    Supports the provided 7-class model (driver/passenger × with/without helmet, plus
    bare driver/passenger/bike) and simpler 2-class helmet models.
    """
    low = label.lower()
    if "without_helmet" in low or "no_helmet" in low or "no-helmet" in low:
        return False
    if "with_helmet" in low or low == "helmet":
        return True
    return None  # bike / driver / passenger -> a rider, but helmet not stated


class YoloHelmetClassifier:
    """Runs a local helmet YOLO model on the FULL image (one inference) and sets
    ``person.helmet`` on graph riders by box overlap. No VLM / API calls — so it has
    no rate limit.

    The model also localises riders (driver/passenger classes), so a confident rider
    box that COCO missed is added as a new rider node — lifting both helmet recall and
    triple-riding counts. ``bike`` boxes are ignored (COCO already has them).
    """

    def __init__(
        self, weights: str, conf: float = 0.35, match_iou: float = 0.4
    ) -> None:
        self._weights = weights
        self._conf = conf
        self._match_iou = match_iou
        self._model = None  # lazy

    def _load(self):  # noqa: ANN202
        if self._model is None:
            from ultralytics import YOLO  # heavy, lazy

            self._model = YOLO(self._weights)
        return self._model

    def apply(self, graph: EvidenceGraph, image_path: str) -> None:
        model = self._load()
        result = model(image_path, conf=self._conf, verbose=False)[0]
        names = result.names

        # Collect person-class detections (everything except the 'bike' box).
        dets: list[tuple[BBox, bool | None, float]] = []
        for box in result.boxes:
            label = names[int(box.cls)]
            if label.lower() == "bike":
                continue
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            dets.append(
                (
                    BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    _helmet_verdict(label),
                    float(box.conf),
                )
            )
        apply_helmet_detections(graph, dets, self._match_iou)


def apply_helmet_detections(
    graph: EvidenceGraph,
    dets: list[tuple[BBox, bool | None, float]],
    match_iou: float = 0.4,
) -> None:
    """Pure helmet-box → rider assignment (no model/IO, so it is unit-testable).

    Each ``dets`` item is ``(bbox, verdict, conf)`` where verdict is True/False/None.
    Sets ``helmet``/``helmet_score`` on the best-matching rider, and adds a new rider
    node for a confident box on a motorcycle that no existing rider matched.
    """
    if not dets:
        return

    # NMS among the helmet model's own boxes: prefer definite verdicts, then confidence.
    dets = sorted(dets, key=lambda d: (d[1] is not None, d[2]), reverse=True)
    kept: list[tuple[BBox, bool | None, float]] = []
    for d in dets:
        if all(d[0].iou(k[0]) < 0.5 for k in kept):
            kept.append(d)

    # 1) Assign each helmet box (definite verdicts first) to the rider it best fits. The
    #    model emits small head boxes, so IoU vs a full-body rider box is tiny;
    #    score by the strongest of IoU or either-way containment instead.
    riders = [p for p in graph.persons if p.role == PersonRole.rider]
    assigned: set[str] = set()
    used: set[int] = set()
    for i, (b, verdict, conf) in enumerate(kept):
        best_p, best_ov = None, 0.0
        for p in riders:
            if p.id in assigned:
                continue
            ov = max(
                b.iou(p.bbox),
                b.intersection_over_self(p.bbox),
                p.bbox.intersection_over_self(b),
            )
            if ov > best_ov:
                best_ov, best_p = ov, p
        if best_p is not None and best_ov >= match_iou:
            used.add(i)
            assigned.add(best_p.id)
            if verdict is not None:
                best_p.helmet = verdict
                best_p.helmet_score = conf

    # 2) Augmentation: an unmatched helmet box sitting on a motorcycle is a rider COCO
    #    missed — add it so helmet + triple-riding rules see the full picture.
    for i, (b, verdict, conf) in enumerate(kept):
        if i in used:
            continue
        best_v, best_score = None, 0.0
        for v in graph.vehicles:
            if v.type not in {"motorcycle", "bicycle"}:
                continue
            score = b.intersection_over_self(v.bbox)
            if score > best_score:
                best_score, best_v = score, v
        if best_v is not None and best_score >= 0.3:
            pid = new_id("det")
            graph.persons.append(
                Person(
                    id=pid,
                    role=PersonRole.rider,
                    bbox=b,
                    confidence=conf,
                    helmet=verdict,
                    helmet_score=conf if verdict is not None else None,
                )
            )
            graph.edges.append(Edge(type="rides", src=pid, dst=best_v.id))


_HELMET_PROMPT = (
    "Does the person wear a helmet on their head (a motorcycle or bicycle "
    'helmet)? Reply with ONLY JSON: {"helmet": true} if clearly wearing one, '
    '{"helmet": false} if clearly not, {"helmet": null} if you cannot tell.'
)


class GeminiHelmetClassifier:
    """Reads helmet status per rider crop using the Gemini vision model — no local model
    file needed. Free-tier friendly with retry/backoff; any error leaves helmet
    undetermined (that rider is then simply not flagged).
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

    def apply(self, graph: EvidenceGraph, image_path: str) -> None:
        import io
        import json

        from google.genai import types
        from PIL import Image

        from core.llm import call_with_retry

        riders = [p for p in graph.persons if p.role.value == "rider"]
        if not riders:
            return
        img = Image.open(image_path).convert("RGB")
        for p in riders:
            b = p.bbox
            buf = io.BytesIO()
            img.crop((int(b.x1), int(b.y1), int(b.x2), int(b.y2))).save(buf, "JPEG")
            data = buf.getvalue()
            try:
                resp = call_with_retry(
                    lambda d=data: self._client_obj().models.generate_content(
                        model=self._model,
                        contents=[
                            _HELMET_PROMPT,
                            types.Part.from_bytes(data=d, mime_type="image/jpeg"),
                        ],
                    ),
                    attempts=2,
                    base_delay=3.0,
                )
                text = (
                    (resp.text or "")
                    .strip()
                    .removeprefix("```json")
                    .removeprefix("```")
                )
                value = json.loads(text.removesuffix("```").strip()).get("helmet")
                p.helmet = None if value is None else bool(value)
            except Exception as e:  # noqa: BLE001
                print(f"[gemini.helmet] {type(e).__name__}: {e}", file=sys.stderr)
                p.helmet = None


def get_detector(settings: Settings | None = None) -> Detector:
    settings = settings or get_settings()
    return YoloDetector(settings.detector_weights, settings.detector_conf)


def get_helmet_classifier(settings: Settings | None = None) -> HelmetClassifier:
    settings = settings or get_settings()
    if settings.helmet_weights:
        return YoloHelmetClassifier(
            settings.helmet_weights, settings.helmet_conf, settings.helmet_match_iou
        )
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return GeminiHelmetClassifier(settings.gemini_api_key, settings.gemini_model)
    return NullHelmetClassifier()


def classify_lights(graph: EvidenceGraph, image_path: str) -> None:
    """Set each traffic light's state via HSV colour analysis of its crop. Cheap and
    approximate; only opens the image if lights exist.
    """
    from core.schemas import LightState

    if not graph.lights:
        return
    import numpy as np
    from PIL import Image

    hsv = np.asarray(Image.open(image_path).convert("HSV"))
    h_ch, s_ch, v_ch = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    bright = (s_ch > 80) & (v_ch > 80)  # ignore dim/grey pixels

    for light in graph.lights:
        b = light.bbox
        y1, y2 = int(max(0, b.y1)), int(max(0, b.y2))
        x1, x2 = int(max(0, b.x1)), int(max(0, b.x2))
        m = bright[y1:y2, x1:x2]
        hue = h_ch[y1:y2, x1:x2]
        if m.size == 0 or not m.any():
            continue
        red = int(((hue < 15) | (hue > 240))[m].sum())
        amber = int(((hue >= 15) & (hue < 45))[m].sum())
        green = int(((hue >= 60) & (hue < 110))[m].sum())
        counts = [
            (red, LightState.red),
            (amber, LightState.amber),
            (green, LightState.green),
        ]
        top = max(counts, key=lambda t: t[0])
        light.state = top[1] if top[0] > 0 else LightState.unknown
