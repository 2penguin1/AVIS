"""CLI: python -m eval.run [dataset.json]   (default: eval/sample_dataset.json)

Runs the real pipeline (downloads YOLO weights on first use) over the labelled set and
prints the metrics table used in the pitch.
"""

from __future__ import annotations

import sys

from eval.harness import EvalReport, evaluate, load_dataset
from eval.metrics import PRF


def _table(metrics: dict[str, PRF]) -> str:
    header = f"{'type':<28}{'P':>6}{'R':>6}{'F1':>6}{'TP':>5}{'FP':>5}{'FN':>5}"
    rows = [
        f"{k:<28}{m.precision:6.2f}{m.recall:6.2f}{m.f1:6.2f}{m.tp:5d}{m.fp:5d}{m.fn:5d}"
        for k, m in metrics.items()
    ]
    return "\n".join([header, *rows])


def report(rep: EvalReport) -> str:
    out = [
        f"Samples: {rep.n}   mean latency: {rep.mean_latency_s * 1000:.0f} ms/image",
        "",
        "== rule + VLM (routed; auto/VLM-confirmed only) ==",
        _table(rep.routed),
        f"macro-F1: {rep.macro_f1_routed:.3f}",
        "",
        "== rule-only (ablation; no VLM filtering) ==",
        _table(rep.rule_only),
        f"macro-F1: {rep.macro_f1_rule_only:.3f}",
        "",
        f"Dispositions: {rep.dispositions}",
    ]
    if rep.plate_whole_accuracy is not None:
        out.append(
            f"Plate whole-accuracy: {rep.plate_whole_accuracy:.2f}   "
            f"char-accuracy: {rep.plate_char_accuracy:.2f}"
        )
    out.append(
        "\nNote: object-detection mAP needs bbox-level labels; this harness reports "
        "violation-level metrics. Use the base YOLO model's COCO mAP for detector mAP."
    )
    return "\n".join(out)


def main(path: str = "eval/sample_dataset.json") -> None:
    print(report(evaluate(load_dataset(path))))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "eval/sample_dataset.json")
