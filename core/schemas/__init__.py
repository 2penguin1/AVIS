"""Pydantic payloads for every pipeline stage. The Evidence Graph is the core type."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _utcnow() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #
class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2

    def iou(self, other: BBox) -> float:
        ix1, iy1 = max(self.x1, other.x1), max(self.y1, other.y1)
        ix2, iy2 = min(self.x2, other.x2), min(self.y2, other.y2)
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0

    def intersection_over_self(self, other: BBox) -> float:
        """Fraction of *this* box that lies inside ``other`` (good for rider↔bike)."""
        ix1, iy1 = max(self.x1, other.x1), max(self.y1, other.y1)
        ix2, iy2 = min(self.x2, other.x2), min(self.y2, other.y2)
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        return inter / self.area if self.area > 0 else 0.0


# --------------------------------------------------------------------------- #
# detection
# --------------------------------------------------------------------------- #
class Detection(BaseModel):
    id: str = Field(default_factory=lambda: new_id("det"))
    label: str
    bbox: BBox
    confidence: float


class DetectionResult(BaseModel):
    image_width: int
    image_height: int
    detections: list[Detection] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# evidence graph
# --------------------------------------------------------------------------- #
class PersonRole(str, Enum):
    rider = "rider"
    driver = "driver"
    pedestrian = "pedestrian"


class LightState(str, Enum):
    red = "red"
    amber = "amber"
    green = "green"
    unknown = "unknown"


class Vehicle(BaseModel):
    id: str
    type: str  # car | motorcycle | truck | bus | bicycle
    bbox: BBox
    confidence: float
    in_zones: list[str] = Field(default_factory=list)


class Person(BaseModel):
    id: str
    role: PersonRole
    bbox: BBox
    confidence: float
    helmet: bool | None = None  # None = undetermined
    helmet_score: float | None = None  # classifier confidence for the helmet verdict
    seatbelt: bool | None = None


class Light(BaseModel):
    id: str
    state: LightState = LightState.unknown
    bbox: BBox
    confidence: float


class Plate(BaseModel):
    id: str = Field(default_factory=lambda: new_id("plate"))
    text: str = ""
    regex_ok: bool = False
    confidence: float = 0.0
    bbox: BBox | None = None


class Edge(BaseModel):
    type: str  # rides | drives | has_plate | located_in | governed_by
    src: str
    dst: str


class Zone(BaseModel):
    id: str
    kind: str  # stop_line | no_parking | lane
    polygon: list[tuple[float, float]]
    direction: str | None = None  # for lane zones


class EvidenceGraph(BaseModel):
    image_id: str
    vehicles: list[Vehicle] = Field(default_factory=list)
    persons: list[Person] = Field(default_factory=list)
    lights: list[Light] = Field(default_factory=list)
    plates: list[Plate] = Field(default_factory=list)
    zones: list[Zone] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    def vehicle(self, vid: str) -> Vehicle | None:
        return next((v for v in self.vehicles if v.id == vid), None)

    def person(self, pid: str) -> Person | None:
        return next((p for p in self.persons if p.id == pid), None)

    def node_bbox(self, node_id: str) -> BBox | None:
        for coll in (self.vehicles, self.persons, self.lights):
            hit = next((n for n in coll if n.id == node_id), None)
            if hit is not None:
                return hit.bbox
        return None

    def riders_of(self, vehicle_id: str) -> list[Person]:
        ids = {e.src for e in self.edges if e.type == "rides" and e.dst == vehicle_id}
        return [p for p in self.persons if p.id in ids]

    def drivers_of(self, vehicle_id: str) -> list[Person]:
        ids = {e.src for e in self.edges if e.type == "drives" and e.dst == vehicle_id}
        return [p for p in self.persons if p.id in ids]

    def plate_of(self, vehicle_id: str) -> Plate | None:
        ids = {
            e.dst for e in self.edges if e.type == "has_plate" and e.src == vehicle_id
        }
        return next((p for p in self.plates if p.id in ids), None)

    def zones_by_kind(self, kind: str) -> list[Zone]:
        return [z for z in self.zones if z.kind == kind]


# --------------------------------------------------------------------------- #
# violations
# --------------------------------------------------------------------------- #
class Tier(str, Enum):
    A = "A"  # appearance — may auto-confirm
    B = "B"  # hard appearance (e.g. seatbelt)
    C = "C"  # spatial, needs calibration
    D = "D"  # temporal, candidate only


class Sufficiency(str, Enum):
    sufficient = "sufficient"
    candidate = "candidate"
    insufficient = "insufficient"


class Route(str, Enum):
    auto_confirmed = "auto_confirmed"
    vlm_confirmed = "vlm_confirmed"
    human_review = "human_review"
    abstain = "abstain"


class Scores(BaseModel):
    detection: float = 0.0
    rule: float = 0.0
    attribute: float = 0.0
    vlm: float | None = None
    fused: float = 0.0


class Candidate(BaseModel):
    type: str  # HELMET_NON_COMPLIANCE | TRIPLE_RIDING | ...
    tier: Tier
    subjects: list[str] = Field(default_factory=list)
    rule_score: float
    attribute_score: float = 0.0
    detection_score: float = 0.0
    pre_verified: bool = (
        False  # attribute already decided (e.g. helmet) -> skip 2nd VLM call
    )
    speculative: bool = (
        False  # a guess (e.g. seatbelt) -> drop if the VLM can't confirm it
    )
    reason: str = ""


class Violation(BaseModel):
    id: str = Field(default_factory=lambda: new_id("vio"))
    image_id: str
    type: str
    tier: Tier
    evidence_sufficiency: Sufficiency
    subjects: list[str] = Field(default_factory=list)
    scores: Scores
    route: Route
    reason: str = ""
    plate: Plate | None = None
    legal: dict | None = None
    evidence_hash: str = ""
    annotated_url: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


# --------------------------------------------------------------------------- #
# images
# --------------------------------------------------------------------------- #
class ImageStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    undeterminable = "undeterminable"
    failed = "failed"


class ImageMeta(BaseModel):
    id: str = Field(default_factory=lambda: new_id("img"))
    filename: str
    camera_id: str | None = None
    status: ImageStatus = ImageStatus.pending
    created_at: datetime = Field(default_factory=_utcnow)
