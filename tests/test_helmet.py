"""Helmet-box -> rider assignment is pure (no model/IO), so we test it directly."""

from __future__ import annotations

from core.detect import _helmet_verdict, apply_helmet_detections
from core.schemas import BBox, Edge, EvidenceGraph, Person, PersonRole, Vehicle


def _bbox(x1, y1, x2, y2) -> BBox:
    return BBox(x1=x1, y1=y1, x2=x2, y2=y2)


def test_verdict_mapping() -> None:
    assert _helmet_verdict("driver_without_helmet") is False
    assert _helmet_verdict("passenger_without_helmet") is False
    assert _helmet_verdict("driver_with_helmet") is True
    assert _helmet_verdict("passenger_with_helmet") is True
    assert _helmet_verdict("helmet") is True
    assert _helmet_verdict("driver") is None  # rider present, helmet unknown
    assert _helmet_verdict("passenger") is None


def test_head_box_sets_helmet_on_contained_rider() -> None:
    # Full-body rider box; the model's small 'without_helmet' head box sits inside it.
    # IoU is tiny but containment is high -> must still match (the real-world case).
    rider = Person(
        id="p1", role=PersonRole.rider, bbox=_bbox(80, 34, 396, 457), confidence=0.2
    )
    bike = Vehicle(
        id="v1", type="motorcycle", bbox=_bbox(101, 191, 431, 636), confidence=0.4
    )
    g = EvidenceGraph(
        image_id="i",
        vehicles=[bike],
        persons=[rider],
        edges=[Edge(type="rides", src="p1", dst="v1")],
    )
    apply_helmet_detections(g, [(_bbox(269, 28, 358, 131), False, 0.42)], match_iou=0.4)
    assert g.person("p1").helmet is False
    assert g.person("p1").helmet_score == 0.42


def test_augments_rider_coco_missed() -> None:
    # No riders detected, but a without_helmet box sits on the bike -> add a rider.
    bike = Vehicle(
        id="v1", type="motorcycle", bbox=_bbox(0, 0, 100, 200), confidence=0.5
    )
    g = EvidenceGraph(image_id="i", vehicles=[bike])
    apply_helmet_detections(g, [(_bbox(10, 10, 90, 160), False, 0.6)])
    riders = [p for p in g.persons if p.role == PersonRole.rider]
    assert len(riders) == 1
    assert riders[0].helmet is False
    assert g.riders_of("v1")  # linked by a 'rides' edge


def test_box_off_any_motorcycle_is_ignored() -> None:
    # A car (not a two-wheeler) and a far-away box -> nothing added, no helmet set.
    car = Vehicle(id="v1", type="car", bbox=_bbox(0, 0, 50, 50), confidence=0.5)
    g = EvidenceGraph(image_id="i", vehicles=[car])
    apply_helmet_detections(g, [(_bbox(500, 500, 560, 560), False, 0.6)])
    assert [p for p in g.persons if p.role == PersonRole.rider] == []


def test_empty_detections_is_noop() -> None:
    g = EvidenceGraph(image_id="i")
    apply_helmet_detections(g, [])
    assert g.persons == []
