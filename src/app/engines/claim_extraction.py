"""Extract exact, potentially verifiable statements from messages."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.core.models import Claim, ClaimCategory, Conversation
from app.providers.base import LLMProvider


class _Candidate(BaseModel):
    message_order: int
    original_statement: str
    category: ClaimCategory = ClaimCategory.FACTUAL
    confidence: float = Field(default=60, ge=0, le=100)


class _Extraction(BaseModel):
    claims: list[_Candidate]


_OPINION = re.compile(
    r"^(?:in my opinion|i think|i feel|i like|i dislike|i prefer|to me|it seems to me)\b",
    re.IGNORECASE,
)
_HYPOTHETICAL = re.compile(r"^(?:if\b|suppose\b|imagine\b|what if\b|let us say\b)", re.IGNORECASE)
_SPECULATIVE = re.compile(r"^(?:maybe|perhaps|probably|possibly|i guess|i suspect)\b", re.IGNORECASE)
_CREATIVE = re.compile(
    r"\b(?:as a joke|just kidding|in this story|in this poem|metaphorically|sarcasm|irony|fictionally)\b",
    re.IGNORECASE,
)
_METAPHOR = re.compile(r"\b(?:is|was) (?:a|an) (?:blanket|ocean|river|wall|storm|bridge)\b", re.IGNORECASE)
_FACTUAL_CUES = re.compile(
    r"\b(?:is|are|was|were|has|have|had|weighs?|contains?|holds?|causes?|caused|"
    r"increases?|decreases?|equals?|measured?|occurred|exists?|will|must|cannot|can be)\b|\d",
    re.IGNORECASE,
)


class ClaimExtractionEngine:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def extract_claims(self, conversation: Conversation) -> list[Claim]:
        if self.provider is not None:
            prompt = (
                "Extract individually testable factual assertions from this conversation. "
                "Exclude opinions, questions, hypotheticals, jokes, metaphors, speculation, and creative language. "
                "Return exact verbatim substrings only. message_order is zero-based. "
                "Do not infer speaker identity or missing context.\n"
                + "\n".join(f"[{m.order}] {m.text}" for m in conversation.messages)
            )
            result = self.provider.analyze_structured(
                prompt,
                _Extraction,
                system_prompt="Classify statements conservatively and preserve exact source wording.",
            )
            return self._from_candidates(conversation, result.claims)

        claims: list[Claim] = []
        for message in conversation.messages:
            for sentence in self._sentences(message.text):
                if self._is_factual_claim(sentence):
                    claims.append(
                        Claim(
                            original_statement=sentence,
                            speaker_id=message.speaker_id,
                            message_id=message.id,
                            category=ClaimCategory.FACTUAL,
                            surrounding_context=self._surrounding_context(conversation, message.order),
                            extraction_confidence=60,
                        )
                    )
        return claims

    def _from_candidates(self, conversation: Conversation, candidates: list[_Candidate]) -> list[Claim]:
        messages_by_order = {message.order: message for message in conversation.messages}
        output: list[Claim] = []
        for candidate in candidates:
            message = messages_by_order.get(candidate.message_order)
            if not message or candidate.category != ClaimCategory.FACTUAL:
                continue
            wording = candidate.original_statement.strip()
            if not wording or wording not in message.text:
                continue
            output.append(
                Claim(
                    original_statement=wording,
                    speaker_id=message.speaker_id,
                    message_id=message.id,
                    category=candidate.category,
                    surrounding_context=self._surrounding_context(conversation, message.order),
                    extraction_confidence=candidate.confidence,
                )
            )
        return output

    def _sentences(self, text: str) -> list[str]:
        # Remove no wording: strip only the outer whitespace around each sentence.
        return [sentence.strip() for sentence in re.split(r"(?<=[.!?。？！])\s+", text.strip()) if sentence.strip()]

    def _is_factual_claim(self, text: str) -> bool:
        if text.endswith(("?", "？")):
            return False
        if _OPINION.match(text) or _HYPOTHETICAL.match(text) or _SPECULATIVE.match(text):
            return False
        if _CREATIVE.search(text) or _METAPHOR.search(text):
            return False
        return bool(_FACTUAL_CUES.search(text))

    @staticmethod
    def _surrounding_context(conversation: Conversation, order: int) -> str:
        messages = conversation.messages[max(0, order - 1): order + 2]
        return "\n".join(
            f"{message.speaker_id}: {message.text}" if message.speaker_id else message.text
            for message in messages
        )
