"""Pure metric functions — no I/O, fully unit-testable."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


def prf(tp: int, fp: int, fn: int) -> PRF:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return PRF(p, r, f, tp, fp, fn)


def confusion(
    expected: list[set[str]], predicted: list[set[str]], labels: list[str]
) -> dict[str, PRF]:
    """Per-label P/R/F1 from per-sample expected/predicted label sets."""
    out: dict[str, PRF] = {}
    for lab in labels:
        tp = fp = fn = 0
        for exp, pred in zip(expected, predicted, strict=True):
            in_e, in_p = lab in exp, lab in pred
            if in_e and in_p:
                tp += 1
            elif in_p and not in_e:
                fp += 1
            elif in_e and not in_p:
                fn += 1
        out[lab] = prf(tp, fp, fn)
    return out


def macro_f1(metrics: dict[str, PRF]) -> float:
    return sum(m.f1 for m in metrics.values()) / len(metrics) if metrics else 0.0


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def char_accuracy(pred: str, gold: str) -> float:
    if not gold:
        return 1.0 if not pred else 0.0
    return max(0.0, 1.0 - levenshtein(pred, gold) / len(gold))
