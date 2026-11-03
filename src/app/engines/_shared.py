"""Helpers shared by independent analysis engines."""

from __future__ import annotations

import re

from app.core.models import (
    Claim,
    Conversation,
    Evidence,
    EvidenceSourceType,
    Message,
)


def contexts_by_message(conversation: Conversation, radius: int = 1) -> dict[str, str]:
    contexts: dict[str, str] = {}
    for index, message in enumerate(conversation.messages):
        start = max(0, index - radius)
        end = min(len(conversation.messages), index + radius + 1)
        contexts[message.id] = "\n".join(
            f"{item.speaker_id}: {item.text}" if item.speaker_id else item.text
            for item in conversation.messages[start:end]
        )
    return contexts


def evidence_for_claim(claim: Claim, *, content: str | None = None) -> Evidence:
    return Evidence(
        source_type=EvidenceSourceType.CONVERSATION,
        source_reference=claim.message_id,
        relevant_content=content or claim.original_statement,
        reliability_assessment=(
            "This records what a participant said; it is not independent proof of the claim."
        ),
    )


def message_for_claim(conversation: Conversation, claim: Claim) -> Message | None:
    return next((message for message in conversation.messages if message.id == claim.message_id), None)


def normalized_statement(text: str) -> str:
    return re.sub(r"[^\w]+", " ", text.casefold()).strip()


def has_correction_cue(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:correction|i meant|to clarify|let me clarify|i was wrong|actually|i misspoke|"
            r"i changed my mind|my view changed|rather)\b",
            text,
            re.IGNORECASE,
        )
    )


def explicit_time_markers(text: str) -> set[str]:
    markers = {
        "yesterday", "today", "tomorrow", "now", "currently", "formerly",
        "last week", "this week", "next week", "last year", "this year", "next year",
        "in the past", "in the future",
    }
    lowered = text.casefold()
    found = {marker for marker in markers if re.search(rf"\b{re.escape(marker)}\b", lowered)}
    found.update(re.findall(r"\b(?:19|20)\d{2}\b", lowered))
    return found
