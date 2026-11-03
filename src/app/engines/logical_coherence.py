"""Identify and explain common reasoning failures."""

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


class _Fallacy(BaseModel):
    message_order: int
    original_statement: str
    category: str
    explanation: str
    confidence: float = Field(default=55, ge=0, le=100)
    related_statement: str | None = None


class _Fallacies(BaseModel):
    findings: list[_Fallacy]


class LogicalCoherenceEngine:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def analyze(self, conversation: Conversation) -> list[Finding]:
        if self.provider is not None:
            transcript = "\n".join(f"[{m.order}] {m.text}" for m in conversation.messages)
            prompt = (
                "Identify explicit reasoning errors such as circular reasoning, false cause, hasty generalization, "
                "unsupported causal assumptions, non sequiturs, invalid conclusions, and false dilemmas. "
                "Explain the missing premise or invalid inference; do not return a fallacy label alone. "
                "Do not repeat a finding that is only a factual disagreement or an absurdity. Quote exact text.\n"
                + transcript
            )
            result = self.provider.analyze_structured(prompt, _Fallacies)
            return self._from_fallacies(conversation, result.findings)

        findings: list[Finding] = []
        for message in conversation.messages:
            for sentence in re.split(r"(?<=[.!?])\s+", message.text.strip()):
                sentence = sentence.strip()
                if not sentence:
                    continue
                identified = self._classify(sentence)
                if not identified:
                    continue
                category, explanation = identified
                findings.append(
                    Finding(
                        type=FindingType.LOGICAL_FALLACY,
                        status=VerificationStatus.NOT_APPLICABLE,
                        severity=3,
                        confidence=58,
                        speaker=message.speaker_id,
                        original_statement=sentence,
                        explanation=f"{category}: {explanation}",
                        evidence=[
                            Evidence(
                                source_type=EvidenceSourceType.CONVERSATION,
                                source_reference=message.id,
                                relevant_content=sentence,
                                reliability_assessment="Evidence of the argument as stated; premises may be omitted.",
                            )
                        ],
                        context=message.text,
                        limitations=["The full argument or unstated premises may affect the assessment."],
                    )
                )
        return findings

    @staticmethod
    def _classify(sentence: str) -> tuple[str, str] | None:
        text = sentence.casefold()
        if re.search(r"\b(?:either .+ or .+|if you are not .+ you are)\b", text):
            return (
                "false_dilemma",
                "The wording presents two choices as exhaustive without establishing that no alternatives exist.",
            )
        if re.search(r"\b(?:one|a single|this one)\b.{0,60}\b(?:proves?|shows?)\b.{0,40}\b(?:all|every|always)\b", text):
            return (
                "hasty_generalization",
                "A broad conclusion is drawn from one case without evidence that the case represents the full group.",
            )
        if "because" in text:
            before, after = text.split("because", maxsplit=1)
            words = {word for word in re.findall(r"\w+", before) if len(word) > 3}
            reason_words = {word for word in re.findall(r"\w+", after) if len(word) > 3}
            if words and len(words & reason_words) >= min(2, len(words)):
                return (
                    "circular_reasoning",
                    "The explanation restates the conclusion instead of giving an independent reason for it.",
                )
        if re.search(r"\b(?:so|therefore|thus)\b", text) and re.search(r"\b(?:caused?|must be the reason|proves?)\b", text):
            return (
                "unsupported_causal_inference",
                "The conclusion assigns a cause from the stated outcome without showing a causal link or ruling out alternatives.",
            )
        if re.search(r"\b(?:after .+ therefore|happened after .+ so)\b", text):
            return (
                "false_cause",
                "Sequence in time alone does not establish that the earlier event caused the later one.",
            )
        return None

    @staticmethod
    def _from_fallacies(conversation: Conversation, items: list[_Fallacy]) -> list[Finding]:
        by_order = {message.order: message for message in conversation.messages}
        output = []
        for item in items:
            message = by_order.get(item.message_order)
            if not message or item.original_statement not in message.text:
                continue
            output.append(
                Finding(
                    type=FindingType.LOGICAL_FALLACY,
                    status=VerificationStatus.NOT_APPLICABLE,
                    severity=3,
                    confidence=item.confidence,
                    speaker=message.speaker_id,
                    original_statement=item.original_statement,
                    related_statement=item.related_statement,
                    explanation=f"{item.category}: {item.explanation}",
                    evidence=[
                        Evidence(
                            source_type=EvidenceSourceType.CONVERSATION,
                            source_reference=message.id,
                            relevant_content=item.original_statement,
                            reliability_assessment="Evidence of the argument as stated; premises may be omitted.",
                        )
                    ],
                    context=message.text,
                    limitations=["The complete argument and its premises may affect the assessment."],
                )
            )
        return output
