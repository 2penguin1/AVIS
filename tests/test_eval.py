"""Evaluation harness: pure metrics + an end-to-end run with injected fakes."""

from __future__ import annotations

from core.llm import NullLLM
from core.schemas import BBox, Detection, DetectionResult
from eval.harness import Sample, evaluate
from eval.metrics import char_accuracy, confusion, levenshtein, macro_f1, prf
from tests.conftest import FakeDetector, FakeHelmet


def test_prf() -> None:
    m = prf(8, 2, 0)
    assert round(m.precision, 2) == 0.8
    assert m.recall == 1.0


def test_levenshtein_and_char_accuracy() -> None:
    assert levenshtein("abc", "abd") == 1
    assert char_accuracy("UP32AB1234", "UP32AB1234") == 1.0
    assert 0.0 < char_accuracy("UP32AB1230", "UP32AB1234") < 1.0


def test_confusion_and_macro() -> None:
    metrics = confusion([{"A"}, {"B"}], [{"A"}, {"A"}], ["A", "B"])
    assert metrics["A"].tp == 1 and metrics["A"].fp == 1
    assert metrics["B"].fn == 1
    assert 0.0 <= macro_f1(metrics) <= 1.0


def _three_rider_scene() -> DetectionResult:
    def d(label, box):
        return Detection(
            label=label,
            bbox=BBox(x1=box[0], y1=box[1], x2=box[2], y2=box[3]),
            confidence=0.9,
        )

    return DetectionResult(
        image_width=200,
        image_height=200,
        detections=[
            d("motorcycle", (10, 60, 90, 150)),
            d("person", (15, 20, 45, 130)),
            d("person", (40, 20, 70, 130)),
            d("person", (60, 20, 90, 130)),
        ],
    )


def test_evaluate_ablation_with_fakes() -> None:
    ds = [Sample(image="x.jpg", expected={"HELMET_NON_COMPLIANCE", "TRIPLE_RIDING"})]
    rep = evaluate(
        ds,
        detector=FakeDetector(_three_rider_scene()),
        helmet=FakeHelmet(False),
        llm=NullLLM(),
    )
    assert rep.n == 1
    # rule-only catches both candidates
    assert rep.rule_only["HELMET_NON_COMPLIANCE"].tp == 1
    assert rep.rule_only["TRIPLE_RIDING"].tp == 1
    # routed: helmet auto-confirms; triple (no VLM) -> human review, so it's a miss here
    assert rep.routed["HELMET_NON_COMPLIANCE"].tp == 1
    assert rep.routed["TRIPLE_RIDING"].fn == 1
