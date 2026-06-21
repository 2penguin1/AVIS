"""Rule Engine is pure -> test it with hand-built graphs, no models or I/O."""

from __future__ import annotations

from core.rules import helmet_rule, run_rules, seatbelt_rule, triple_riding_rule
from core.schemas import BBox, Edge, EvidenceGraph, Person, PersonRole, Tier, Vehicle


def _bike(vid: str = "v1") -> Vehicle:
    return Vehicle(
        id=vid, type="motorcycle", bbox=BBox(x1=0, y1=0, x2=50, y2=80), confidence=0.9
    )


def _rider(pid: str, helmet: bool | None) -> Person:
    return Person(
        id=pid,
        role=PersonRole.rider,
        bbox=BBox(x1=5, y1=0, x2=45, y2=40),
        confidence=0.8,
        helmet=helmet,
    )


def _graph(persons: list[Person], vid: str = "v1") -> EvidenceGraph:
    return EvidenceGraph(
        image_id="img_test",
        vehicles=[_bike(vid)],
        persons=persons,
        edges=[Edge(type="rides", src=p.id, dst=vid) for p in persons],
    )


def test_helmet_violation_when_rider_has_no_helmet() -> None:
    g = _graph([_rider("p1", helmet=False)])
    cands = helmet_rule(g)
    assert len(cands) == 1
    assert cands[0].type == "HELMET_NON_COMPLIANCE"
    assert cands[0].tier == Tier.A
    assert cands[0].rule_score == 1.0


def test_no_helmet_violation_when_rider_compliant() -> None:
    g = _graph([_rider("p1", helmet=True)])
    assert helmet_rule(g) == []


def test_unknown_helmet_is_not_flagged() -> None:
    # helmet None = classifier couldn't tell => not a violation (no noise row)
    g = _graph([_rider("p1", helmet=None)])
    assert helmet_rule(g) == []


def test_triple_riding_when_three_riders() -> None:
    g = _graph([_rider("p1", True), _rider("p2", True), _rider("p3", True)])
    cands = triple_riding_rule(g)
    assert len(cands) == 1
    assert cands[0].type == "TRIPLE_RIDING"
    assert "v1" in cands[0].subjects


def test_no_triple_riding_with_two_riders() -> None:
    g = _graph([_rider("p1", True), _rider("p2", True)])
    assert triple_riding_rule(g) == []


def test_run_rules_aggregates() -> None:
    g = _graph([_rider("p1", False), _rider("p2", True), _rider("p3", True)])
    types = {c.type for c in run_rules(g)}
    assert types == {"HELMET_NON_COMPLIANCE", "TRIPLE_RIDING"}


# --- seatbelt (Tier B) ----------------------------------------------------- #
def _car_with_driver(seatbelt: bool | None) -> EvidenceGraph:
    car = Vehicle(
        id="c1", type="car", bbox=BBox(x1=0, y1=0, x2=100, y2=100), confidence=0.9
    )
    drv = Person(
        id="d1",
        role=PersonRole.driver,
        bbox=BBox(x1=10, y1=10, x2=60, y2=90),
        confidence=0.8,
        seatbelt=seatbelt,
    )
    return EvidenceGraph(
        image_id="i",
        vehicles=[car],
        persons=[drv],
        edges=[Edge(type="drives", src="d1", dst="c1")],
    )


def test_seatbelt_candidate_is_speculative_tier_b() -> None:
    cands = seatbelt_rule(_car_with_driver(None))
    assert len(cands) == 1
    assert cands[0].type == "SEATBELT_NON_COMPLIANCE"
    assert cands[0].tier == Tier.B
    assert cands[0].speculative is True


def test_no_seatbelt_candidate_without_a_driver() -> None:
    car = Vehicle(
        id="c1", type="car", bbox=BBox(x1=0, y1=0, x2=100, y2=100), confidence=0.9
    )
    assert seatbelt_rule(EvidenceGraph(image_id="i", vehicles=[car])) == []


def test_no_seatbelt_candidate_when_visibly_belted() -> None:
    assert seatbelt_rule(_car_with_driver(True)) == []
