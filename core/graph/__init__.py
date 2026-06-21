"""Builds the Evidence Graph from raw detections — the single source of truth.

Associates each person to the vehicle their box overlaps most (rider↔motorcycle,
driver↔car); unassociated people become pedestrians.
"""

from __future__ import annotations

from core.schemas import (
    DetectionResult,
    Edge,
    EvidenceGraph,
    Light,
    Person,
    PersonRole,
    Plate,
    Vehicle,
)

VEHICLE_LABELS = {"car", "motorcycle", "motorbike", "truck", "bus", "bicycle"}
TWO_WHEELER = {"motorcycle", "bicycle"}


def _norm(label: str) -> str:
    return "motorcycle" if label == "motorbike" else label


def build_graph(
    image_id: str, det: DetectionResult, assoc_threshold: float = 0.15
) -> EvidenceGraph:
    vehicles: list[Vehicle] = [
        Vehicle(id=d.id, type=_norm(d.label), bbox=d.bbox, confidence=d.confidence)
        for d in det.detections
        if d.label in VEHICLE_LABELS
    ]
    lights: list[Light] = [
        Light(id=d.id, bbox=d.bbox, confidence=d.confidence)
        for d in det.detections
        if d.label == "traffic light"
    ]

    persons: list[Person] = []
    edges: list[Edge] = []
    for d in det.detections:
        if d.label != "person":
            continue
        best: Vehicle | None = None
        best_score = 0.0
        for v in vehicles:
            score = d.bbox.intersection_over_self(v.bbox)
            if score > best_score:
                best_score, best = score, v
        if best is not None and best_score >= assoc_threshold:
            is_two = best.type in TWO_WHEELER
            role = PersonRole.rider if is_two else PersonRole.driver
            edge_type = "rides" if is_two else "drives"
            persons.append(
                Person(id=d.id, role=role, bbox=d.bbox, confidence=d.confidence)
            )
            edges.append(Edge(type=edge_type, src=d.id, dst=best.id))
        else:
            persons.append(
                Person(
                    id=d.id,
                    role=PersonRole.pedestrian,
                    bbox=d.bbox,
                    confidence=d.confidence,
                )
            )

    return EvidenceGraph(
        image_id=image_id,
        vehicles=vehicles,
        persons=persons,
        lights=lights,
        edges=edges,
    )


def attach_plates(
    graph: EvidenceGraph, plates: list[Plate], threshold: float = 0.5
) -> None:
    """Attach each detected plate to the vehicle whose box it sits inside."""
    for plate in plates:
        graph.plates.append(plate)
        if plate.bbox is None:
            continue
        best: Vehicle | None = None
        best_score = 0.0
        for v in graph.vehicles:
            score = plate.bbox.intersection_over_self(v.bbox)
            if score > best_score:
                best_score, best = score, v
        if best is not None and best_score >= threshold:
            graph.edges.append(Edge(type="has_plate", src=best.id, dst=plate.id))
