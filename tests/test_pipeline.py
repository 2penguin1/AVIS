"""End-to-end pipeline wiring (detection injected): graph -> rules -> fuse -> route ->
legal -> annotate. No CV models or network needed.
"""

from __future__ import annotations

from core.llm import NullLLM
from core.pipeline import process
from core.schemas import BBox, Detection, DetectionResult, Route, Sufficiency
from tests.conftest import FakeDetector, FakeHelmet


def _det(label, box, conf=0.9):
    return Detection(
        label=label,
        bbox=BBox(x1=box[0], y1=box[1], x2=box[2], y2=box[3]),
        confidence=conf,
    )


def _three_rider_scene() -> DetectionResult:
    return DetectionResult(
        image_width=200,
        image_height=200,
        detections=[
            _det("motorcycle", (10, 60, 90, 150)),
            _det("person", (15, 20, 45, 130)),
            _det("person", (40, 20, 70, 130)),
            _det("person", (60, 20, 90, 130)),
        ],
    )


def test_pipeline_flags_helmet_and_triple_riding() -> None:
    violations, graph = process(
        "img_pipe",
        "unused.jpg",
        detector=FakeDetector(_three_rider_scene()),
        helmet=FakeHelmet(False),
        llm=NullLLM(),
    )
    by_type = {v.type: v for v in violations}
    assert "HELMET_NON_COMPLIANCE" in by_type
    assert "TRIPLE_RIDING" in by_type

    # Helmet: rule_score 1.0 + strong detection/attribute -> Tier A auto-confirm.
    assert by_type["HELMET_NON_COMPLIANCE"].route == Route.auto_confirmed
    # Triple riding: lower fused (no attribute signal) + no VLM -> human review.
    assert by_type["TRIPLE_RIDING"].route == Route.human_review

    # Legal grounding attached.
    assert by_type["HELMET_NON_COMPLIANCE"].legal["section"] == "194D"


class _UnavailableLLM:
    enabled = True

    def verify(self, image_path: str, vtype: str, reason: str) -> dict:
        return {
            "verified": False,
            "confidence": 0.0,
            "reason": "VLM unavailable or could not judge the evidence.",
            "insufficient_evidence": False,
            "verifier_unavailable": True,
        }


class _InsufficientEvidenceLLM:
    enabled = True

    def verify(self, image_path: str, vtype: str, reason: str) -> dict:
        return {
            "verified": False,
            "confidence": 0.0,
            "reason": "The image is too unclear to verify this violation.",
            "insufficient_evidence": True,
            "verifier_unavailable": False,
        }


def test_vlm_unavailable_routes_triple_riding_to_human_review() -> None:
    violations, _ = process(
        "img_vlm_down",
        "unused.jpg",
        detector=FakeDetector(_three_rider_scene()),
        helmet=FakeHelmet(True),
        llm=_UnavailableLLM(),
    )

    triple = next(v for v in violations if v.type == "TRIPLE_RIDING")
    assert triple.route == Route.human_review
    assert triple.evidence_sufficiency == Sufficiency.candidate


def test_vlm_insufficient_evidence_still_abstains() -> None:
    violations, _ = process(
        "img_unclear",
        "unused.jpg",
        detector=FakeDetector(_three_rider_scene()),
        helmet=FakeHelmet(True),
        llm=_InsufficientEvidenceLLM(),
    )

    triple = next(v for v in violations if v.type == "TRIPLE_RIDING")
    assert triple.route == Route.abstain
    assert triple.evidence_sufficiency == Sufficiency.insufficient


class _PositiveLLM:
    enabled = True

    def verify(self, image_path: str, vtype: str, reason: str) -> dict:
        return {
            "verified": True,
            "confidence": 0.9,
            "reason": "Clearly supported.",
            "insufficient_evidence": False,
            "verifier_unavailable": False,
        }


class _NegativeLLM:
    enabled = True

    def verify(self, image_path: str, vtype: str, reason: str) -> dict:
        return {
            "verified": False,
            "confidence": 0.2,
            "reason": "The driver appears belted.",
            "insufficient_evidence": False,
            "verifier_unavailable": False,
        }


def _speculative_seatbelt():
    from core.schemas import Candidate, Tier

    return Candidate(
        type="SEATBELT_NON_COMPLIANCE",
        tier=Tier.B,
        subjects=["c1", "d1"],
        rule_score=0.5,
        detection_score=0.9,
        speculative=True,
        reason="check belt",
    )


def test_speculative_dropped_when_vlm_cannot_confirm() -> None:
    from core.config import Settings
    from core.pipeline import _adjudicate
    from core.schemas import EvidenceGraph

    v = _adjudicate(
        _speculative_seatbelt(),
        EvidenceGraph(image_id="i"),
        "x.jpg",
        _NegativeLLM(),
        Settings(),
    )
    assert v.route == Route.abstain
    assert v.evidence_sufficiency == Sufficiency.insufficient


def test_speculative_dropped_when_no_vlm() -> None:
    from core.config import Settings
    from core.pipeline import _adjudicate
    from core.schemas import EvidenceGraph

    v = _adjudicate(
        _speculative_seatbelt(),
        EvidenceGraph(image_id="i"),
        "x.jpg",
        NullLLM(),
        Settings(),
    )
    assert v.route == Route.abstain


def test_speculative_confirmed_when_vlm_positive() -> None:
    from core.config import Settings
    from core.pipeline import _adjudicate
    from core.schemas import EvidenceGraph

    v = _adjudicate(
        _speculative_seatbelt(),
        EvidenceGraph(image_id="i"),
        "x.jpg",
        _PositiveLLM(),
        Settings(),
    )
    assert v.route == Route.vlm_confirmed


def test_annotate_writes_a_copy(tmp_path) -> None:
    from PIL import Image

    from core import evidence

    src = tmp_path / "src.jpg"
    Image.new("RGB", (200, 200), (40, 40, 40)).save(src)

    violations, graph = process(
        "img_annot",
        str(src),
        detector=FakeDetector(_three_rider_scene()),
        helmet=FakeHelmet(False),
        llm=NullLLM(),
    )
    out = tmp_path / "out.jpg"
    evidence.annotate(str(src), str(out), violations, graph)
    assert out.exists()
    assert evidence.hash_image(str(src))  # non-empty digest
