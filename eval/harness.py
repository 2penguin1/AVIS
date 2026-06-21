"""Run the pipeline over a labelled dataset and compute metrics.

Ground truth is image-level: each sample lists the violation *types* truly present
(plus an optional ground-truth plate). We report violation-level Precision/Recall/F1
two ways — **rule-only** (every rule candidate) vs **rule+VLM routed** (only auto/VLM
confirmed) — which is the ablation that shows what the VLM verification buys.

Detection mAP needs bbox-level annotations and is out of scope for this image-level
harness; use the base detector's COCO mAP for object-detection mAP.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from core.pipeline import process
from core.schemas import Route
from eval.metrics import PRF, char_accuracy, confusion, macro_f1

CONFIRMED = {Route.auto_confirmed.value, Route.vlm_confirmed.value}

ALL_TYPES = [
    "HELMET_NON_COMPLIANCE",
    "TRIPLE_RIDING",
    "SEATBELT_NON_COMPLIANCE",
    "STOP_LINE_VIOLATION",
    "RED_LIGHT_VIOLATION",
    "ILLEGAL_PARKING",
    "WRONG_SIDE_DRIVING",
]


@dataclass
class Sample:
    image: str
    expected: set[str]
    camera_id: str | None = None
    plate: str | None = None


@dataclass
class EvalReport:
    n: int
    rule_only: dict[str, PRF]
    routed: dict[str, PRF]
    macro_f1_rule_only: float
    macro_f1_routed: float
    dispositions: dict[str, int]
    mean_latency_s: float
    plate_whole_accuracy: float | None
    plate_char_accuracy: float | None


def load_dataset(path: str) -> list[Sample]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return [
        Sample(
            image=s["image"],
            expected=set(s.get("expected", [])),
            camera_id=s.get("camera_id"),
            plate=s.get("plate"),
        )
        for s in data["samples"]
    ]


def evaluate(
    dataset: list[Sample], *, labels: list[str] | None = None, **pipeline_kwargs
) -> EvalReport:
    labels = labels or ALL_TYPES
    expected: list[set[str]] = []
    pred_rule_only: list[set[str]] = []
    pred_routed: list[set[str]] = []
    dispositions: dict[str, int] = {}
    latencies: list[float] = []
    plate_whole: list[float] = []
    plate_char: list[float] = []

    for s in dataset:
        t0 = time.perf_counter()
        violations, graph = process(
            "eval", s.image, camera_id=s.camera_id, **pipeline_kwargs
        )
        latencies.append(time.perf_counter() - t0)

        expected.append(s.expected)
        pred_rule_only.append({v.type for v in violations})
        pred_routed.append({v.type for v in violations if v.route.value in CONFIRMED})
        for v in violations:
            dispositions[v.route.value] = dispositions.get(v.route.value, 0) + 1

        if s.plate:
            reads = [p.text for p in graph.plates if p.text]
            pred_plate = reads[0] if reads else ""
            plate_whole.append(1.0 if pred_plate == s.plate else 0.0)
            plate_char.append(char_accuracy(pred_plate, s.plate))

    rule_only = confusion(expected, pred_rule_only, labels)
    routed = confusion(expected, pred_routed, labels)
    return EvalReport(
        n=len(dataset),
        rule_only=rule_only,
        routed=routed,
        macro_f1_rule_only=macro_f1(rule_only),
        macro_f1_routed=macro_f1(routed),
        dispositions=dispositions,
        mean_latency_s=(sum(latencies) / len(latencies)) if latencies else 0.0,
        plate_whole_accuracy=(sum(plate_whole) / len(plate_whole))
        if plate_whole
        else None,
        plate_char_accuracy=(sum(plate_char) / len(plate_char)) if plate_char else None,
    )
