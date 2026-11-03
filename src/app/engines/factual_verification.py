"""Verify claims only against supplied or explicitly configured evidence."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.core.models import (
    Claim,
    Conversation,
    Evidence,
    EvidenceSourceType,
    VerificationResult,
    VerificationStatus,
)
from app.engines._shared import explicit_time_markers, has_correction_cue, normalized_statement
from app.providers.base import LLMProvider
from app.providers.evidence import EvidenceProvider


class _Verification(BaseModel):
    status: VerificationStatus
    evidence: list[Evidence] = Field(default_factory=list)
    explanation: str
    confidence: float = Field(ge=0, le=100)
    limitations: list[str] = Field(default_factory=list)


_OPPOSITES = (("full", "empty"), ("open", "closed"), ("on", "off"), ("present", "absent"))
_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_NEGATION = re.compile(r"\b(?:not|never|no|cannot|can't|isn't|aren't|wasn't|weren't|doesn't|don't|didn't)\b", re.I)


class FactualVerificationEngine:
    def __init__(
        self,
        provider: LLMProvider | None = None,
        evidence_provider: EvidenceProvider | None = None,
    ) -> None:
        self.provider = provider
        self.evidence_provider = evidence_provider

    def verify(
        self,
        claim: Claim,
        evidence: list[Evidence] | None = None,
        conversation: Conversation | None = None,
    ) -> VerificationResult:
        supplied = list(evidence or [])
        if self.evidence_provider is not None:
            supplied.extend(self.evidence_provider.search(claim.original_statement))
        if self.provider is not None:
            evidence_text = "\n".join(
                f"[{item.source_type}] {item.source_reference or ''}: {item.relevant_content} "
                f"(reliability: {item.reliability_assessment})"
                for item in supplied
            ) or "No external or user-provided evidence was supplied."
            prompt = (
                "Assess only this factual claim against the supplied evidence. Do not invent sources. "
                "Use UNVERIFIED when evidence is insufficient; do not use FALSE without reliable evidence. "
                "A conflicting statement in the conversation establishes a contradiction, not intent.\n"
                f"Claim: {claim.original_statement}\nEvidence:\n{evidence_text}"
            )
            result = self.provider.analyze_structured(prompt, _Verification)
            if result.status in {VerificationStatus.FALSE, VerificationStatus.VERIFIED} and not result.evidence:
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.UNVERIFIED,
                    evidence=[],
                    explanation="The model returned a conclusive label without evidence, so it was downgraded.",
                    confidence=0,
                    limitations=result.limitations + ["No cited evidence was available to support a conclusive status."],
                )
            return VerificationResult(claim=claim, **result.model_dump())

        for item in supplied:
            if self._same_proposition(claim.original_statement, item.relevant_content):
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.SUPPORTED,
                    evidence=[item],
                    explanation="The supplied evidence contains the same proposition.",
                    confidence=65,
                    limitations=["The reliability of the supplied source has not been independently audited."],
                )
            if self._explicit_conflict(claim.original_statement, item.relevant_content):
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.CONTRADICTED,
                    evidence=[item],
                    explanation="The supplied evidence explicitly conflicts with the claim.",
                    confidence=70,
                    limitations=["This evidence supports a conflict but does not establish a speaker's intent."],
                )

        if conversation:
            for message in conversation.messages:
                if message.id == claim.message_id:
                    continue
                source_message = next(
                    (item for item in conversation.messages if item.id == claim.message_id), None
                )
                if source_message:
                    first_times = explicit_time_markers(source_message.text)
                    other_times = explicit_time_markers(message.text)
                    if first_times and other_times and first_times != other_times:
                        continue
                    if (
                        source_message.speaker_id == message.speaker_id
                        and (has_correction_cue(source_message.text) or has_correction_cue(message.text))
                    ):
                        continue
                if self._explicit_conflict(claim.original_statement, message.text):
                    item = Evidence(
                        source_type=EvidenceSourceType.CONVERSATION,
                        source_reference=message.id,
                        relevant_content=message.text,
                        reliability_assessment="A conflicting participant statement; not independent fact-checking.",
                    )
                    return VerificationResult(
                        claim=claim,
                        status=VerificationStatus.CONTRADICTED,
                        evidence=[item],
                        explanation="Another message explicitly conflicts with this claim.",
                        confidence=65,
                        limitations=["Conversation disagreement does not by itself establish which statement is true."],
                    )

        if supplied:
            limitation = "The available sources did not resolve the claim; their completeness is unknown."
        elif self.evidence_provider is not None:
            limitation = "The configured evidence endpoint returned no relevant source for this claim."
        else:
            limitation = "UNVERIFIED does not mean FALSE; no external source was queried."
        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIED,
            evidence=supplied,
            explanation="No source available to this run independently verifies or refutes the claim.",
            confidence=0,
            limitations=[limitation],
        )

    @staticmethod
    def _same_proposition(claim: str, evidence: str) -> bool:
        normalized_claim = normalized_statement(claim)
        normalized_evidence = normalized_statement(evidence)
        return bool(normalized_claim and normalized_claim in normalized_evidence)

    @staticmethod
    def _explicit_conflict(claim: str, evidence: str) -> bool:
        claim_tokens = set(normalized_statement(claim).split())
        evidence_tokens = set(normalized_statement(evidence).split())
        shared = claim_tokens & evidence_tokens
        if len(shared) < 2:
            return False
        claim_numbers, evidence_numbers = _NUMBER.findall(claim), _NUMBER.findall(evidence)
        if claim_numbers and evidence_numbers and claim_numbers != evidence_numbers:
            return True
        if bool(_NEGATION.search(claim)) != bool(_NEGATION.search(evidence)):
            return True
        first, second = claim.casefold(), evidence.casefold()
        return any((a in first and b in second) or (b in first and a in second) for a, b in _OPPOSITES)
