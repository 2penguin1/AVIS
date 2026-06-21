"""Detector wiring: configurable confidence should flow into the YOLO call."""

from __future__ import annotations

from core.detect import YoloDetector


class _FakeTensor:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return list(self._values)

    def __iter__(self):
        return iter(self._values)

    def __getitem__(self, idx):
        if idx == 0:
            return self
        raise IndexError(idx)


class _FakeBox:
    def __init__(
        self, cls_id: int, conf: float, xyxy: tuple[float, float, float, float]
    ) -> None:
        self.cls = cls_id
        self.conf = conf
        self.xyxy = _FakeTensor(xyxy)


class _FakeResult:
    names = {0: "person", 3: "motorcycle"}
    orig_shape = (100, 200)

    def __init__(self) -> None:
        self.boxes = [_FakeBox(3, 0.12, (1.0, 2.0, 30.0, 40.0))]


class _FakeModel:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, image_path: str, **kwargs):
        self.calls.append({"image_path": image_path, **kwargs})
        return [_FakeResult()]


def test_yolo_detector_uses_configured_confidence() -> None:
    model = _FakeModel()
    detector = YoloDetector("unused.pt", conf=0.05)
    detector._model = model

    result = detector.detect("frame.jpg")

    assert model.calls == [{"image_path": "frame.jpg", "verbose": False, "conf": 0.05}]
    assert len(result.detections) == 1
    assert result.detections[0].label == "motorcycle"
