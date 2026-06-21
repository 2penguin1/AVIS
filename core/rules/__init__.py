"""Deterministic, pure Rule Engine. One function per violation; emits *candidates*.

No ML, no I/O, no randomness here — that is what makes it unit-testable in isolation.

Tiers (see docs/DESIGN.md §3):
  A  appearance       — helmet, triple riding (may auto-confirm downstream)
  C  spatial          — stop-line, red-light, illegal parking (need camera calibration;
                        never auto-confirm; routed to VLM/human)
  D  temporal         — wrong-side (a still image can't prove it; stays inert by design)
"""

from __future__ import annotations

from collections.abc import Callable

from core.calibration import point_in_polygon
from core.schemas import Candidate, EvidenceGraph, LightState, Tier, Vehicle

Rule = Callable[[EvidenceGraph], list[Candidate]]


def _ground_point(v: Vehicle) -> tuple[float, float]:
    """Bottom-centre of the box ~ where the vehicle meets the road."""
    return (v.bbox.x1 + v.bbox.x2) / 2, v.bbox.y2


# --------------------------------------------------------------------------- #
# Tier A — appearance
# --------------------------------------------------------------------------- #
def helmet_rule(graph: EvidenceGraph) -> list[Candidate]:
    out: list[Candidate] = []
    for v in graph.vehicles:
        if v.type not in {"motorcycle", "bicycle"}:
            continue
        for r in graph.riders_of(v.id):
            # helmet None => the classifier could not tell; not a reportable violation.
            if r.helmet is False:
                out.append(
                    Candidate(
                        type="HELMET_NON_COMPLIANCE",
                        tier=Tier.A,
                        subjects=[v.id, r.id],
                        rule_score=1.0,
                        # use the classifier's real confidence when we have it
                        attribute_score=r.helmet_score
                        if r.helmet_score is not None
                        else 0.9,
                        detection_score=v.confidence,
                        pre_verified=True,  # set by the classifier; skip the 2nd VLM
                        reason="A rider on a motorcycle is not wearing a helmet.",
                    )
                )
    return out


# --------------------------------------------------------------------------- #
# Tier B — hard appearance (seatbelt: genuinely unreliable from traffic cams)
# --------------------------------------------------------------------------- #
def seatbelt_rule(graph: EvidenceGraph) -> list[Candidate]:
    """Flag car/truck/bus drivers for a seatbelt check. Tier B: a still image rarely
    proves it, so these are ``speculative`` candidates routed to the VLM/human — never
    auto-confirmed, and dropped if the VLM can't substantiate them.
    """
    out: list[Candidate] = []
    for v in graph.vehicles:
        if v.type not in {"car", "truck", "bus"}:
            continue
        for d in graph.drivers_of(v.id):
            if d.seatbelt is True:
                continue  # visibly belted -> no violation
            speculative = (
                d.seatbelt is None
            )  # None = a guess; False = classifier said so
            out.append(
                Candidate(
                    type="SEATBELT_NON_COMPLIANCE",
                    tier=Tier.B,
                    subjects=[v.id, d.id],
                    rule_score=0.5 if speculative else 0.8,
                    detection_score=v.confidence,
                    speculative=speculative,
                    reason=(
                        "A driver is visible in a car; a seatbelt check is needed."
                        if speculative
                        else "A car driver appears not to be wearing a seatbelt."
                    ),
                )
            )
    return out


def triple_riding_rule(graph: EvidenceGraph) -> list[Candidate]:
    out: list[Candidate] = []
    for v in graph.vehicles:
        if v.type != "motorcycle":
            continue
        riders = graph.riders_of(v.id)
        if len(riders) >= 3:
            out.append(
                Candidate(
                    type="TRIPLE_RIDING",
                    tier=Tier.A,
                    subjects=[v.id, *[r.id for r in riders]],
                    rule_score=min(1.0, len(riders) / 3.0),
                    detection_score=v.confidence,
                    reason=f"{len(riders)} riders are linked to a single motorcycle.",
                )
            )
    return out


# --------------------------------------------------------------------------- #
# Tier C — spatial (require per-camera calibration zones; never auto-confirm)
# --------------------------------------------------------------------------- #
def stop_line_rule(graph: EvidenceGraph) -> list[Candidate]:
    out: list[Candidate] = []
    for z in graph.zones_by_kind("stop_line"):
        for v in graph.vehicles:
            if point_in_polygon(_ground_point(v), z.polygon):
                out.append(
                    Candidate(
                        type="STOP_LINE_VIOLATION",
                        tier=Tier.C,
                        subjects=[v.id],
                        rule_score=0.8,
                        detection_score=v.confidence,
                        reason="Vehicle is over the calibrated stop-line zone.",
                    )
                )
    return out


def red_light_rule(graph: EvidenceGraph) -> list[Candidate]:
    if not any(light.state == LightState.red for light in graph.lights):
        return []
    out: list[Candidate] = []
    for z in graph.zones_by_kind("stop_line"):
        for v in graph.vehicles:
            if point_in_polygon(_ground_point(v), z.polygon):
                out.append(
                    Candidate(
                        type="RED_LIGHT_VIOLATION",
                        tier=Tier.C,
                        subjects=[v.id],
                        rule_score=0.7,
                        detection_score=v.confidence,
                        reason="Light is red and vehicle is past the stop line; "
                        "confirm with an image sequence.",
                    )
                )
    return out


def illegal_parking_rule(graph: EvidenceGraph) -> list[Candidate]:
    out: list[Candidate] = []
    for z in graph.zones_by_kind("no_parking"):
        for v in graph.vehicles:
            if point_in_polygon(_ground_point(v), z.polygon):
                out.append(
                    Candidate(
                        type="ILLEGAL_PARKING",
                        tier=Tier.C,
                        subjects=[v.id],
                        rule_score=0.6,
                        detection_score=v.confidence,
                        reason="Vehicle is inside a no-parking zone; "
                        "needs dwell-time confirmation.",
                    )
                )
    return out


# --------------------------------------------------------------------------- #
# Tier D — temporal (a single frame cannot prove it; inert by design)
# --------------------------------------------------------------------------- #
def wrong_side_rule(graph: EvidenceGraph) -> list[Candidate]:
    """Direction of travel needs motion; a still image can't establish it. We abstain
    rather than emit false positives — fill in once orientation/tracking exists."""
    return []


RULES: list[Rule] = [
    helmet_rule,
    triple_riding_rule,
    seatbelt_rule,
    stop_line_rule,
    red_light_rule,
    illegal_parking_rule,
    wrong_side_rule,
]


def run_rules(graph: EvidenceGraph) -> list[Candidate]:
    candidates: list[Candidate] = []
    for rule in RULES:
        candidates.extend(rule(graph))
    return candidates
