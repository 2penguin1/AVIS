"""Test doubles so the pipeline can be exercised without downloading CV models."""

from __future__ import annotations

from core.schemas import DetectionResult, EvidenceGraph


class FakeDetector:
    def __init__(self, result: DetectionResult) -> None:
        self._result = result

    def detect(self, image_path: str) -> DetectionResult:
        return self._result


class FakeHelmet:
    """Sets every rider's helmet status to a fixed value (default: not wearing)."""

    def __init__(self, helmet: bool | None = False) -> None:
        self._helmet = helmet

    def apply(self, graph: EvidenceGraph, image_path: str) -> None:
        for p in graph.persons:
            if p.role.value == "rider":
                p.helmet = self._helmet
