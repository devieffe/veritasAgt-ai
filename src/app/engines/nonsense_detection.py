"""Conservative semantic-absurdity checks, kept separate from contradictions."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.core.models import (
    Conversation,
    Evidence,
    EvidenceSourceType,
    Finding,
    FindingType,
    VerificationStatus,
)
from app.providers.base import LLMProvider


class _Absurdity(BaseModel):
    message_order: int
    original_statement: str
    category: str
    explanation: str
    severity: int = Field(ge=0, le=5)
    confidence: float = Field(ge=0, le=100)
    limitations: list[str] = Field(default_factory=list)


class _Absurdities(BaseModel):
    findings: list[_Absurdity]


_CREATIVE = re.compile(
    r"\b(?:as a joke|just kidding|metaphor|in this story|in this poem|fiction|sarcasm|irony|wordplay)\b",
    re.I,
)
_ABSURD_CONSEQUENCE = re.compile(
    r"\b(?:the )?(?:sun|moon|planet|universe|gravity|time)\b.{0,55}\b(?:cease to exist|vanish from existence|"
    r"disappear from the universe|turn into nothing)\b",
    re.I,
)
_CATEGORY_ERROR = re.compile(r"\b(?:square root of|weighs? exactly)\s+(?:monday|tuesday|a color|the color)\b", re.I)


class NonsenseDetectionEngine:
    """Detect absurd implications without treating unusual factual claims as nonsense."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def detect(self, conversation: Conversation) -> list[Finding]:
        if self.provider is not None:
            transcript = "\n".join(f"[{m.order}] {m.text}" for m in conversation.messages)
            prompt = (
                "Independently identify semantic incoherence, category errors, impossible causal relationships, "
                "non sequiturs, and absurd conclusions. Do not treat an unlikely factual claim as nonsense; "
                "classify it as an assertion requiring verification. Exclude metaphor, irony, sarcasm, humor, "
                "wordplay, fiction, paradox, and explicit hypotheticals unless context makes a literal assertion "
                "clear. Quote the exact sentence.\n" + transcript
            )
            result = self.provider.analyze_structured(prompt, _Absurdities)
            return self._from_absurdities(conversation, result.findings)

        findings: list[Finding] = []
        for message in conversation.messages:
            for sentence in re.split(r"(?<=[.!?])\s+", message.text.strip()):
                sentence = sentence.strip()
                if not sentence or _CREATIVE.search(sentence):
                    continue
                if _ABSURD_CONSEQUENCE.search(sentence) and re.search(r"\b(?:if|when|because|so|therefore|causes?)\b", sentence, re.I):
                    category = "absurd_causal_conclusion"
                    explanation = (
                        "The stated cause does not provide a plausible mechanism for the claimed destruction "
                        "of a celestial or physical system. This is a reasoning problem, not a judgment about a person."
                    )
                elif _CATEGORY_ERROR.search(sentence):
                    category = "category_error"
                    explanation = "The statement applies a mathematical or physical property to a category that does not support it."
                else:
                    continue
                findings.append(
                    Finding(
                        type=FindingType.NONSENSE,
                        status=VerificationStatus.NOT_APPLICABLE,
                        severity=5,
                        confidence=85,
                        speaker=message.speaker_id,
                        original_statement=sentence,
                        explanation=f"{category}: {explanation}",
                        evidence=[
                            Evidence(
                                source_type=EvidenceSourceType.CONVERSATION,
                                source_reference=message.id,
                                relevant_content=sentence,
                                reliability_assessment="Evidence of the statement and its local context.",
                            )
                        ],
                        context=message.text,
                        limitations=["A fictional, ironic, or omitted context could change the reading."],
                    )
                )
        return findings

    @staticmethod
    def _from_absurdities(conversation: Conversation, items: list[_Absurdity]) -> list[Finding]:
        by_order = {message.order: message for message in conversation.messages}
        findings = []
        for item in items:
            message = by_order.get(item.message_order)
            if not message or item.original_statement not in message.text:
                continue
            findings.append(
                Finding(
                    type=FindingType.NONSENSE,
                    status=VerificationStatus.NOT_APPLICABLE,
                    severity=item.severity,
                    confidence=item.confidence,
                    speaker=message.speaker_id,
                    original_statement=item.original_statement,
                    explanation=f"{item.category}: {item.explanation}",
                    evidence=[
                        Evidence(
                            source_type=EvidenceSourceType.CONVERSATION,
                            source_reference=message.id,
                            relevant_content=item.original_statement,
                            reliability_assessment="Evidence of the wording and local context.",
                        )
                    ],
                    context=message.text,
                    limitations=item.limitations,
                )
            )
        return findings
