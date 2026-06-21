"""Scene-graph association: riders link to the motorcycle they overlap."""

from __future__ import annotations

from core.graph import build_graph
from core.schemas import BBox, Detection, DetectionResult, PersonRole


def _det(
    label: str, box: tuple[float, float, float, float], conf: float = 0.9
) -> Detection:
    return Detection(
        label=label,
        bbox=BBox(x1=box[0], y1=box[1], x2=box[2], y2=box[3]),
        confidence=conf,
    )


def test_rider_associates_to_overlapping_motorcycle() -> None:
    det = DetectionResult(
        image_width=200,
        image_height=200,
        detections=[
            _det("motorcycle", (10, 60, 60, 140)),
            _det("person", (15, 20, 55, 130)),  # sits on the bike, overlaps heavily
        ],
    )
    g = build_graph("img1", det)
    assert len(g.vehicles) == 1
    riders = g.riders_of(g.vehicles[0].id)
    assert len(riders) == 1
    assert riders[0].role == PersonRole.rider


def test_far_person_is_pedestrian() -> None:
    det = DetectionResult(
        image_width=400,
        image_height=200,
        detections=[
            _det("motorcycle", (10, 60, 60, 140)),
            _det("person", (300, 20, 340, 120)),  # nowhere near the bike
        ],
    )
    g = build_graph("img2", det)
    assert g.riders_of(g.vehicles[0].id) == []
    assert g.persons[0].role == PersonRole.pedestrian


def test_three_riders_link_to_one_bike() -> None:
    det = DetectionResult(
        image_width=200,
        image_height=200,
        detections=[
            _det("motorcycle", (10, 60, 90, 150)),
            _det("person", (15, 20, 45, 130)),
            _det("person", (40, 20, 70, 130)),
            _det("person", (60, 20, 90, 130)),
        ],
    )
    g = build_graph("img3", det)
    assert len(g.riders_of(g.vehicles[0].id)) == 3
