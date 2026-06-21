"""Plate normalisation + attachment to the vehicle it sits inside."""

from __future__ import annotations

from core.graph import attach_plates
from core.plates import ChainPlateRecognizer, _as_conf, normalize_plate
from core.schemas import BBox, EvidenceGraph, Plate, Vehicle


def _car(vid: str, box: tuple[float, float, float, float]) -> Vehicle:
    return Vehicle(
        id=vid,
        type="car",
        bbox=BBox(x1=box[0], y1=box[1], x2=box[2], y2=box[3]),
        confidence=0.9,
    )


def test_normalize_valid_indian_plate() -> None:
    assert normalize_plate("up 32 ab 1234") == ("UP32AB1234", True)


def test_normalize_rejects_garbage() -> None:
    cleaned, ok = normalize_plate("!!??")
    assert ok is False
    assert cleaned == ""


def test_plate_attaches_to_enclosing_vehicle() -> None:
    g = EvidenceGraph(image_id="i", vehicles=[_car("v1", (0, 0, 100, 100))])
    plate = Plate(
        text="UP32AB1234",
        regex_ok=True,
        confidence=0.8,
        bbox=BBox(x1=40, y1=70, x2=70, y2=85),
    )
    attach_plates(g, [plate])
    got = g.plate_of("v1")
    assert got is not None
    assert got.text == "UP32AB1234"


def test_plate_outside_vehicle_is_not_attached() -> None:
    g = EvidenceGraph(image_id="i", vehicles=[_car("v1", (0, 0, 50, 50))])
    plate = Plate(
        text="UP32AB1234",
        regex_ok=True,
        confidence=0.8,
        bbox=BBox(x1=200, y1=200, x2=230, y2=215),
    )
    attach_plates(g, [plate])
    assert g.plate_of("v1") is None


def test_as_conf_collapses_list_to_mean() -> None:
    assert _as_conf([0.8, 0.6]) == 0.7
    assert _as_conf(0.5) == 0.5
    assert _as_conf(None) == 0.0


class _Fixed:
    def __init__(self, plates: list[Plate]) -> None:
        self._plates = plates

    def read_all(self, image_path: str) -> list[Plate]:
        return self._plates


def test_chain_uses_primary_when_it_reads_a_plate() -> None:
    chain = ChainPlateRecognizer(
        _Fixed([Plate(text="UP32AB1234")]), _Fixed([Plate(text="ZZ")])
    )
    assert chain.read_all("x")[0].text == "UP32AB1234"


def test_chain_falls_back_when_primary_is_empty() -> None:
    chain = ChainPlateRecognizer(_Fixed([]), _Fixed([Plate(text="MH01AA1111")]))
    assert chain.read_all("x")[0].text == "MH01AA1111"
