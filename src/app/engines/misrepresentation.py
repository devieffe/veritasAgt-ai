"""Describe observable misleading communication patterns without inferring intent."""

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


class _Pattern(BaseModel):
    message_order: int
    original_statement: str
    category: str
    explanation: str
    confidence: float = Field(default=55, ge=0, le=100)
    related_statement: str | None = None


class _Patterns(BaseModel):
    findings: list[_Pattern]


_UNSUPPORTED_SCOPE = re.compile(r"\b(?:all|every|everyone|always|never|no one|none|everywhere)\b", re.I)
_SELECTIVE = re.compile(r"\b(?:only the cases|does not count|doesn't count|left out|ignored the other)\b", re.I)
_GOALPOST = re.compile(r"\b(?:that does not count|that doesn't count|now the requirement|the rule has changed)\b", re.I)


class MisrepresentationDetectionEngine:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def detect(self, conversation: Conversation) -> list[Finding]:
        if self.provider is not None:
            transcript = "\n".join(
                f"[{message.order}] {message.speaker_id or 'unknown'}: {message.text}"
                for message in conversation.messages
            )
            prompt = (
                "Identify only observable selective presentation, false attribution, unsupported universal "
                "generalization, misleading comparison, cherry-picking, moving goalposts, or distortion of an "
                "earlier statement. Quote the exact source sentence. Explain the missing context. Do not infer "
                "intent or dishonesty.\n" + transcript
            )
            result = self.provider.analyze_structured(prompt, _Patterns)
            return self._from_patterns(conversation, result.findings)

        findings: list[Finding] = []
        for message in conversation.messages:
            for sentence in re.split(r"(?<=[.!?])\s+", message.text.strip()):
                sentence = sentence.strip()
                if not sentence:
                    continue
                if _GOALPOST.search(sentence):
                    category = "moving_goalposts"
                    explanation = (
                        "The statement appears to replace or dismiss a stated criterion; compare it with the "
                        "earlier criterion before drawing a conclusion."
                    )
                elif _SELECTIVE.search(sentence):
                    category = "selective_presentation"
                    explanation = (
                        "The wording signals that some cases or context may have been excluded; the omitted "
                        "material is needed to assess the comparison."
                    )
                elif _UNSUPPORTED_SCOPE.search(sentence):
                    category = "unsupported_generalization"
                    explanation = (
                        "The statement uses an absolute quantifier. The conversation does not establish that "
                        "the claim applies to every case."
                    )
                else:
                    continue
                findings.append(
                    Finding(
                        type=FindingType.MISREPRESENTATION,
                        status=VerificationStatus.MISLEADING,
                        severity=2,
                        confidence=48,
                        speaker=message.speaker_id,
                        original_statement=sentence,
                        explanation=f"Observed pattern ({category}): {explanation} No intent is inferred.",
                        evidence=[
                            Evidence(
                                source_type=EvidenceSourceType.CONVERSATION,
                                source_reference=message.id,
                                relevant_content=sentence,
                                reliability_assessment="Evidence of the wording used, not of the speaker's intent.",
                            )
                        ],
                        context=message.text,
                        limitations=["The broader context or supporting data may justify the wording."],
                    )
                )
        return findings

    @staticmethod
    def _from_patterns(conversation: Conversation, patterns: list[_Pattern]) -> list[Finding]:
        by_order = {message.order: message for message in conversation.messages}
        output = []
        for item in patterns:
            message = by_order.get(item.message_order)
            if not message or item.original_statement not in message.text:
                continue
            output.append(
                Finding(
                    type=FindingType.MISREPRESENTATION,
                    status=VerificationStatus.MISLEADING,
                    severity=2,
                    confidence=item.confidence,
                    speaker=message.speaker_id,
                    original_statement=item.original_statement,
                    related_statement=item.related_statement,
                    explanation=f"Observed pattern ({item.category}): {item.explanation} No intent is inferred.",
                    evidence=[
                        Evidence(
                            source_type=EvidenceSourceType.CONVERSATION,
                            source_reference=message.id,
                            relevant_content=item.original_statement,
                            reliability_assessment="Evidence of the wording used, not of the speaker's intent.",
                        )
                    ],
                    context=message.text,
                    limitations=["A complete transcript and supporting evidence may change this interpretation."],
                )
            )
        return output
