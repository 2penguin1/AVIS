"""Tier-C calibration rules + point-in-polygon."""

from __future__ import annotations

from core.calibration import point_in_polygon
from core.rules import illegal_parking_rule, red_light_rule, stop_line_rule
from core.schemas import (
    BBox,
    EvidenceGraph,
    Light,
    LightState,
    Tier,
    Vehicle,
    Zone,
)

STOP_LINE = Zone(
    id="sl", kind="stop_line", polygon=[(0, 380), (800, 380), (800, 430), (0, 430)]
)
NO_PARK = Zone(
    id="np", kind="no_parking", polygon=[(600, 100), (780, 100), (780, 320), (600, 320)]
)


def _veh(box: tuple[float, float, float, float]) -> Vehicle:
    return Vehicle(
        id="v1",
        type="car",
        bbox=BBox(x1=box[0], y1=box[1], x2=box[2], y2=box[3]),
        confidence=0.9,
    )


def test_point_in_polygon() -> None:
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert point_in_polygon((5, 5), square)
    assert not point_in_polygon((50, 50), square)


def test_stop_line_violation() -> None:
    g = EvidenceGraph(
        image_id="i", vehicles=[_veh((100, 300, 200, 400))], zones=[STOP_LINE]
    )
    cands = stop_line_rule(g)
    assert len(cands) == 1
    assert cands[0].type == "STOP_LINE_VIOLATION"
    assert cands[0].tier == Tier.C  # never auto-confirms


def test_red_light_only_when_light_red() -> None:
    veh = _veh((100, 300, 200, 400))
    g_green = EvidenceGraph(
        image_id="i",
        vehicles=[veh],
        zones=[STOP_LINE],
        lights=[
            Light(
                id="tl",
                state=LightState.green,
                bbox=BBox(x1=0, y1=0, x2=5, y2=5),
                confidence=0.9,
            )
        ],
    )
    assert red_light_rule(g_green) == []

    g_red = g_green.model_copy(deep=True)
    g_red.lights[0].state = LightState.red
    assert len(red_light_rule(g_red)) == 1


def test_illegal_parking_in_no_parking_zone() -> None:
    g = EvidenceGraph(
        image_id="i", vehicles=[_veh((650, 200, 700, 300))], zones=[NO_PARK]
    )
    cands = illegal_parking_rule(g)
    assert len(cands) == 1
    assert cands[0].type == "ILLEGAL_PARKING"
