"""Evidence integrity + annotated-image composition. The original image is never
modified — we hash it and draw on a copy.
"""

from __future__ import annotations

import hashlib

from core.schemas import EvidenceGraph, Route, Violation

_ROUTE_COLOR = {
    Route.auto_confirmed: (220, 30, 30),
    Route.vlm_confirmed: (240, 140, 0),
    Route.human_review: (210, 180, 0),
    Route.abstain: (130, 130, 130),
}


def hash_image(image_path: str) -> str:
    h = hashlib.sha256()
    with open(image_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def annotate(
    image_path: str,
    out_path: str,
    violations: list[Violation],
    graph: EvidenceGraph,
) -> None:
    from PIL import Image, ImageDraw

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # faint context: all detected vehicles
    for v in graph.vehicles:
        b = v.bbox
        draw.rectangle([b.x1, b.y1, b.x2, b.y2], outline=(70, 130, 220), width=2)

    # violation subjects, coloured by disposition
    for vio in violations:
        color = _ROUTE_COLOR.get(vio.route, (220, 30, 30))
        label = f"{vio.type} {vio.scores.fused:.2f} [{vio.route.value}]"
        for sid in vio.subjects:
            nb = graph.node_bbox(sid)
            if nb is None:
                continue
            draw.rectangle([nb.x1, nb.y1, nb.x2, nb.y2], outline=color, width=3)
        first = graph.node_bbox(vio.subjects[0]) if vio.subjects else None
        if first is not None:
            draw.text((first.x1, max(0, first.y1 - 12)), label, fill=color)
            if vio.plate is not None and vio.plate.text:
                draw.text(
                    (first.x1, first.y2 + 2), f"plate {vio.plate.text}", fill=color
                )

    img.save(out_path)
