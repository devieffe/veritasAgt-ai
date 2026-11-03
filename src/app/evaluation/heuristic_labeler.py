"""Deterministic heuristic labeler for unlabeled chat datasets.

This module intentionally stays offline and dependency-free so it can be used to
bootstrap "silver" labels. It is not intended to produce human-quality gold
truth; instead it creates a repeatable starting point that can be reviewed and
edited.
"""

from __future__ import annotations

import re

from app.evaluation.evaluator import EvaluationCategory


_CORRECTION_RE = re.compile(r"\b(actually|correction:|i\s+mean(t)?|sorry,?\s+i\s+misread)\b", re.I)
_MISREPRESENTATION_RE = re.compile(
    r"\b(i\s+never\s+said\s+that|you\s+never\s+said\s+that|that's\s+a\s+lie|liar)\b",
    re.I,
)
_UNCERTAINTY_RE = re.compile(r"\b(maybe|probably|i\s+think|not\s+sure|unsure|guess)\b", re.I)
_OVERCONFIDENT_RE = re.compile(r"\b(100%|definitely|for\s+sure|no\s+doubt|guarantee)\b", re.I)
_EVIDENCE_RE = re.compile(r"\b(see\s+attached|attachment|screenshot|link:|http[s]?://)\b", re.I)


_ANTONYM_PAIRS: tuple[tuple[str, str], ...] = (
    ("yes", "no"),
    ("open", "closed"),
    ("on", "off"),
    ("true", "false"),
    ("full", "empty"),
    ("here", "there"),
)


def label_conversation(conversation: str) -> list[EvaluationCategory]:
    """Return deterministic heuristic labels for a conversation."""

    text = conversation.strip()
    if not text:
        return []

    lowered = text.casefold()
    labels: set[EvaluationCategory] = set()

    # Claims: any concrete assertion (very broad by design).
    if re.search(r"\b(is|are|was|were|will|did|sent|paid|met|said|told)\b", lowered) or re.search(
        r"\d", lowered
    ):
        labels.add(EvaluationCategory.CLAIM_EXTRACTION)

    # Corrections and temporal/context adjustments.
    if _CORRECTION_RE.search(text):
        labels.add(EvaluationCategory.CONTEXT_AWARENESS)

    # Misrepresentation accusations.
    if _MISREPRESENTATION_RE.search(text):
        labels.update({EvaluationCategory.MISREPRESENTATION_DETECTION, EvaluationCategory.FACTUAL_VERIFICATION})

    # Evidence references.
    if _EVIDENCE_RE.search(text):
        labels.add(EvaluationCategory.EVIDENCE_GROUNDING)

    # Uncertainty / confidence.
    if _UNCERTAINTY_RE.search(text) or _OVERCONFIDENT_RE.search(text):
        labels.add(EvaluationCategory.UNCERTAINTY_CALIBRATION)

    # Factual content heuristic.
    if re.search(r"\b(today|tomorrow|yesterday|at\s+\d|am|pm|\d{1,2}:\d{2})\b", lowered) or re.search(
        r"\b(price|bank|invoice|receipt|contract|address|email)\b", lowered
    ):
        labels.add(EvaluationCategory.FACTUAL_VERIFICATION)

    # Contradiction heuristic: basic antonym co-occurrence.
    for left, right in _ANTONYM_PAIRS:
        if re.search(rf"\b{re.escape(left)}\b", lowered) and re.search(rf"\b{re.escape(right)}\b", lowered):
            labels.add(EvaluationCategory.CONTRADICTION_DETECTION)
            break

    # Nonsense heuristic: heavy punctuation / repeated fragments.
    letters = sum(ch.isalpha() for ch in text)
    if letters:
        non_letters = len(text) - letters
        if non_letters / len(text) > 0.45:
            labels.update({EvaluationCategory.NONSENSE_DETECTION, EvaluationCategory.SEMANTIC_COHERENCE})

    return sorted(labels, key=lambda item: item.value)

