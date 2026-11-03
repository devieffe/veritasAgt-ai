"""Detect explicit conflicts while excluding corrections and time changes."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.core.models import (
    Claim,
    Conversation,
    Evidence,
    EvidenceSourceType,
    Finding,
    FindingType,
    VerificationStatus,
)
from app.engines._shared import explicit_time_markers, has_correction_cue
from app.providers.base import LLMProvider
from app.utils.text_processing import tokenize


class _Pair(BaseModel):
    first_claim_id: str
    second_claim_id: str
    explanation: str
    confidence: float = Field(default=80, ge=0, le=100)


class _Detection(BaseModel):
    contradictions: list[_Pair]


_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "to", "of",
    "and", "or", "but", "in", "on", "at", "by", "for", "from", "with", "it", "this",
    "that", "there", "i", "we", "they", "you", "he", "she", "not", "no", "never",
}
_OPPOSITES = (("full", "empty"), ("open", "closed"), ("on", "off"), ("present", "absent"), ("alive", "dead"))
_NEGATION = re.compile(r"\b(?:not|never|no|cannot|can't|isn't|aren't|wasn't|weren't|doesn't|don't|didn't)\b", re.I)
_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\b")


class ContradictionDetectionEngine:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def detect(self, claims: list[Claim], conversation: Conversation | None = None) -> list[Finding]:
        if self.provider is not None:
            prompt = (
                "Compare these claims and return only genuine conflicts. Exclude corrections, clarifications, "
                "changes of opinion, different times, different perspectives, and ambiguous wording. "
                "Never infer dishonesty.\n"
                + "\n".join(f"{c.id} | {c.speaker_id or 'unknown'} | {c.original_statement}" for c in claims)
            )
            result = self.provider.analyze_structured(prompt, _Detection)
            by_id = {claim.id: claim for claim in claims}
            findings = []
            for pair in result.contradictions:
                first, second = by_id.get(pair.first_claim_id), by_id.get(pair.second_claim_id)
                if first and second:
                    findings.append(self._finding(first, second, pair.explanation, pair.confidence, conversation))
            return findings

        findings: list[Finding] = []
        for index, first in enumerate(claims):
            for second in claims[index + 1:]:
                if self._has_contextual_difference(first, second):
                    continue
                conflict = self._conflict_kind(first.original_statement, second.original_statement)
                if conflict:
                    findings.append(
                        self._finding(
                            first,
                            second,
                            conflict,
                            78,
                            conversation,
                        )
                    )
        return findings

    @staticmethod
    def _has_contextual_difference(first: Claim, second: Claim) -> bool:
        if has_correction_cue(second.original_statement):
            return True
        first_times = explicit_time_markers(first.original_statement)
        second_times = explicit_time_markers(second.original_statement)
        if first_times and second_times and first_times != second_times:
            return True
        if first.message_id == second.message_id and first.speaker_id == second.speaker_id:
            return False
        if first.original_statement.casefold().startswith(("i think", "i prefer", "i feel")):
            return True
        if second.original_statement.casefold().startswith(("i think", "i prefer", "i feel")):
            return True
        return False

    @staticmethod
    def _conflict_kind(first: str, second: str) -> str | None:
        first_tokens = [token for token in tokenize(first) if token not in _STOPWORDS and not token.isdigit()]
        second_tokens = [token for token in tokenize(second) if token not in _STOPWORDS and not token.isdigit()]
        if not first_tokens or not second_tokens:
            return None
        common = set(first_tokens) & set(second_tokens)
        overlap = len(common) / max(1, min(len(set(first_tokens)), len(set(second_tokens))))
        if overlap < 0.45:
            return None

        first_numbers, second_numbers = _NUMBER.findall(first), _NUMBER.findall(second)
        if first_numbers and second_numbers and first_numbers != second_numbers:
            return "The statements give different numerical values for an overlapping subject."

        lowered_first, lowered_second = first.casefold(), second.casefold()
        if bool(_NEGATION.search(first)) != bool(_NEGATION.search(second)):
            return "One statement negates a proposition that the other states affirmatively."
        if any((left in lowered_first and right in lowered_second) or (right in lowered_first and left in lowered_second)
               for left, right in _OPPOSITES):
            return "The statements use opposing descriptions for an overlapping subject."
        return None

    @staticmethod
    def _finding(
        first: Claim,
        second: Claim,
        explanation: str,
        confidence: float,
        conversation: Conversation | None,
    ) -> Finding:
        speaker = first.speaker_id or second.speaker_id
        labels = {item.id: item.label for item in conversation.speakers} if conversation else {}
        return Finding(
            type=FindingType.CONTRADICTION,
            status=VerificationStatus.CONTRADICTED,
            severity=3,
            confidence=confidence,
            speaker=labels.get(speaker, speaker) if speaker else None,
            original_statement=first.original_statement,
            related_statement=second.original_statement,
            explanation=explanation + " This indicates a conflict between statements, not intent or deception.",
            evidence=[
                Evidence(
                    source_type=EvidenceSourceType.CONVERSATION,
                    source_reference=first.message_id,
                    relevant_content=first.original_statement,
                    reliability_assessment="Transcript evidence of the first statement; not independent proof.",
                ),
                Evidence(
                    source_type=EvidenceSourceType.CONVERSATION,
                    source_reference=second.message_id,
                    relevant_content=second.original_statement,
                    reliability_assessment="Transcript evidence of the second statement; not independent proof.",
                ),
            ],
            context=f"{first.surrounding_context}\n{second.surrounding_context}".strip(),
            limitations=["The statements may rely on omitted context or different definitions."],
        )
