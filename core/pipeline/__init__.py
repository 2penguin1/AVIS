"""Pipeline orchestration: detect -> graph -> attributes -> rules -> fuse -> route ->
VLM verify -> legal. Pure business logic — no storage or file writes happen here
(persistence + annotation live in ``core.queue``), so this stays easy to test.

Routing policy (see docs/DESIGN.md §3, §6):
  * Tier A may auto-confirm when fused >= auto_confirm_threshold.
  * Every other case gets a second opinion: VLM if enabled, else human review.
  * VLM 'insufficient_evidence' -> abstain; verifier errors -> human review.
"""

from __future__ import annotations

from core.calibration import load_zones
from core.config import Settings, get_settings
from core.detect import (
    Detector,
    HelmetClassifier,
    classify_lights,
    get_detector,
    get_helmet_classifier,
)
from core.graph import attach_plates, build_graph
from core.legal import lookup
from core.llm import LLMClient, get_llm
from core.plates import PlateRecognizer, get_plate_recognizer
from core.rules import run_rules
from core.schemas import (
    Candidate,
    EvidenceGraph,
    Route,
    Scores,
    Sufficiency,
    Tier,
    Violation,
)


def _fuse(c: Candidate, settings: Settings, vlm_conf: float | None) -> Scores:
    wd, wr, wa = settings.w_detection, settings.w_rule, settings.w_attribute
    num = wd * c.detection_score + wr * c.rule_score + wa * c.attribute_score
    den = wd + wr + wa
    if vlm_conf is not None:
        num += settings.w_vlm * vlm_conf
        den += settings.w_vlm
    fused = num / den if den > 0 else 0.0
    return Scores(
        detection=c.detection_score,
        rule=c.rule_score,
        attribute=c.attribute_score,
        vlm=vlm_conf,
        fused=fused,
    )


def _adjudicate(
    c: Candidate,
    graph: EvidenceGraph,
    image_path: str,
    llm: LLMClient,
    settings: Settings,
) -> Violation:
    scores = _fuse(c, settings, None)
    reason = c.reason

    if c.tier == Tier.A and scores.fused >= settings.auto_confirm_threshold:
        route, sufficiency = Route.auto_confirmed, Sufficiency.sufficient
    elif c.pre_verified:
        # Attribute already decided by a classifier (e.g. helmet) — don't spend
        # a second VLM call. Confirm if reasonably confident, else send to human review.
        if scores.fused >= settings.review_threshold:
            route, sufficiency = Route.vlm_confirmed, Sufficiency.sufficient
        else:
            route, sufficiency = Route.human_review, Sufficiency.candidate
    elif llm.enabled:
        verdict = llm.verify(image_path, c.type, c.reason)
        reason = verdict.get("reason") or reason
        if verdict.get("verifier_unavailable"):
            # speculative guesses can't be confirmed -> drop, don't flood review
            route, sufficiency = (
                (Route.abstain, Sufficiency.insufficient)
                if c.speculative
                else (Route.human_review, Sufficiency.candidate)
            )
        elif verdict.get("insufficient_evidence"):
            route, sufficiency = Route.abstain, Sufficiency.insufficient
        else:
            scores = _fuse(c, settings, float(verdict.get("confidence", 0.0)))
            confirmed = (
                verdict.get("verified") and scores.fused >= settings.review_threshold
            )
            if confirmed:
                route = Route.vlm_confirmed
                sufficiency = (
                    Sufficiency.sufficient
                    if c.tier == Tier.A
                    else Sufficiency.candidate
                )
            elif c.speculative:
                # the VLM did not confirm our guess (e.g. the driver IS belted) -> drop
                route, sufficiency = Route.abstain, Sufficiency.insufficient
            else:
                route, sufficiency = Route.human_review, Sufficiency.candidate
    elif c.speculative:
        # no VLM to confirm a guess -> drop rather than route a maybe to a human
        route, sufficiency = Route.abstain, Sufficiency.insufficient
    else:
        route, sufficiency = Route.human_review, Sufficiency.candidate

    return Violation(
        image_id=graph.image_id,
        type=c.type,
        tier=c.tier,
        evidence_sufficiency=sufficiency,
        subjects=c.subjects,
        scores=scores,
        route=route,
        reason=reason,
        legal=lookup(c.type),
        plate=graph.plate_of(c.subjects[0]) if c.subjects else None,
    )


def process(
    image_id: str,
    image_path: str,
    *,
    camera_id: str | None = None,
    detector: Detector | None = None,
    helmet: HelmetClassifier | None = None,
    plate_recognizer: PlateRecognizer | None = None,
    llm: LLMClient | None = None,
    settings: Settings | None = None,
) -> tuple[list[Violation], EvidenceGraph]:
    settings = settings or get_settings()
    detector = detector or get_detector(settings)
    helmet = helmet or get_helmet_classifier(settings)
    plate_recognizer = plate_recognizer or get_plate_recognizer(settings)
    llm = llm or get_llm(settings)

    det = detector.detect(image_path)
    graph = build_graph(image_id, det)
    helmet.apply(graph, image_path)
    attach_plates(graph, plate_recognizer.read_all(image_path))
    classify_lights(graph, image_path)
    graph.zones = load_zones(camera_id)
    candidates = run_rules(graph)
    if not settings.seatbelt_check:
        # seatbelt is VLM-verified (quota cost) -> only when explicitly enabled
        candidates = [c for c in candidates if c.type != "SEATBELT_NON_COMPLIANCE"]
    violations = [_adjudicate(c, graph, image_path, llm, settings) for c in candidates]
    return violations, graph
