"""Small text helpers used by offline analytical checks."""

from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalized_key(text: str) -> str:
    return re.sub(r"[^\w]+", " ", normalize_whitespace(text).casefold()).strip()


def split_sentences(text: str) -> list[str]:
    """Split on sentence-final punctuation while preserving each sentence's text."""
    text = normalize_whitespace(text)
    if not text:
        return []
    spans = re.split(r"(?<=[.!?。？！])\s+", text)
    return [span.strip() for span in spans if span.strip()]


def tokenize(text: str) -> list[str]:
    return re.findall(r"[\w]+(?:['’][\w]+)?", text.casefold(), flags=re.UNICODE)
