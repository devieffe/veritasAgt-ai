"""Binary metrics for category-level evaluation."""

from __future__ import annotations

from collections.abc import Iterable


def binary_metrics(expected: Iterable[bool], predicted: Iterable[bool]) -> dict[str, float | int]:
    gold, guesses = list(expected), list(predicted)
    if len(gold) != len(guesses):
        raise ValueError("expected and predicted must have the same number of items")
    tp = sum(actual and guess for actual, guess in zip(gold, guesses))
    tn = sum(not actual and not guess for actual, guess in zip(gold, guesses))
    fp = sum(not actual and guess for actual, guess in zip(gold, guesses))
    fn = sum(actual and not guess for actual, guess in zip(gold, guesses))
    total = len(gold)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "accuracy": (tp + tn) / total if total else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "false_negative_rate": fn / (fn + tp) if fn + tp else 0.0,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "support": total,
    }
