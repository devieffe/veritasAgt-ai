"""Coordinate independent engines into one contextual analysis report."""

from __future__ import annotations

from collections import Counter
from time import perf_counter

from app.core.models import (
    AnalysisReport,
    Conversation,
    Finding,
    FindingType,
    VerificationResult,
    VerificationStatus,
)
from app.core.parser import ConversationParser
from app.engines.claim_extraction import ClaimExtractionEngine
from app.engines.context_analysis import ContextAnalysisEngine
from app.engines.contradiction import ContradictionDetectionEngine
from app.engines.factual_verification import FactualVerificationEngine
from app.engines.logical_coherence import LogicalCoherenceEngine
from app.engines.misrepresentation import MisrepresentationDetectionEngine
from app.engines.nonsense_detection import NonsenseDetectionEngine
from app.providers.base import LLMProvider
from app.providers.evidence import EvidenceProvider


class AnalysisOrchestrator:
    def __init__(
        self,
        *,
        parser: ConversationParser | None = None,
        claim_extractor: ClaimExtractionEngine | None = None,
        contradiction_engine: ContradictionDetectionEngine | None = None,
        verification_engine: FactualVerificationEngine | None = None,
        misrepresentation_engine: MisrepresentationDetectionEngine | None = None,
        nonsense_engine: NonsenseDetectionEngine | None = None,
        logic_engine: LogicalCoherenceEngine | None = None,
        context_engine: ContextAnalysisEngine | None = None,
        provider: LLMProvider | None = None,
        evidence_provider: EvidenceProvider | None = None,
    ) -> None:
        self.parser = parser or ConversationParser()
        self.claim_extractor = claim_extractor or ClaimExtractionEngine(provider)
        self.contradiction_engine = contradiction_engine or ContradictionDetectionEngine(provider)
        self.verification_engine = verification_engine or FactualVerificationEngine(provider, evidence_provider)
        self.misrepresentation_engine = misrepresentation_engine or MisrepresentationDetectionEngine(provider)
        self.nonsense_engine = nonsense_engine or NonsenseDetectionEngine(provider)
        self.logic_engine = logic_engine or LogicalCoherenceEngine(provider)
        self.context_engine = context_engine or ContextAnalysisEngine(provider)
        self.provider = provider
        self.evidence_provider = evidence_provider

    def analyze_conversation(self, conversation: str | Conversation) -> AnalysisReport:
        started = perf_counter()
        parsed = self.parser.parse(conversation) if isinstance(conversation, str) else conversation
        claims = self.claim_extractor.extract_claims(parsed)

        findings = self.contradiction_engine.detect(claims, parsed)
        verification_results = [
            self.verification_engine.verify(claim, conversation=parsed) for claim in claims
        ]
        findings.extend(self._verification_findings(verification_results, parsed))
        findings.extend(self.misrepresentation_engine.detect(parsed))
        findings.extend(self.nonsense_engine.detect(parsed))
        findings.extend(self.logic_engine.analyze(parsed))
        findings = self._deduplicate(findings)

        context_result = self.context_engine.analyze(parsed, findings)
        findings = self._deduplicate(context_result.findings)
        limitations = list(context_result.limitations)
        if self.provider is None:
            limitations.append(
                "Offline mode uses conservative patterns and supplied conversation evidence; it does not query external sources."
            )
        if self.evidence_provider is not None:
            limitations = [
                item for item in limitations if "does not query external sources" not in item
            ]
        if not claims:
            limitations.append("No factual claims were extracted; this does not prove that none were present.")

        status_counts = Counter(result.status for result in verification_results)
        summary = self._summary(len(parsed.messages), len(claims), findings, status_counts)
        metadata = {
            "message_count": len(parsed.messages),
            "claim_count": len(claims),
            "finding_count": len(findings),
            "provider": type(self.provider).__name__ if self.provider else "none",
            "verification_status_counts": dict(status_counts),
            "duration_seconds": round(perf_counter() - started, 6),
            "engines": [
                "claim_extraction", "contradiction", "factual_verification", "misrepresentation",
                "nonsense_detection", "logical_coherence", "context_analysis",
            ],
        }
        return AnalysisReport(
            original_conversation_reference=parsed.id,
            extracted_claims=claims,
            findings=findings,
            overall_summary=summary,
            processing_metadata=metadata,
            analysis_limitations=limitations,
        )

    @staticmethod
    def _verification_findings(results: list[VerificationResult], conversation: Conversation) -> list[Finding]:
        speaker_labels = {speaker.id: speaker.label for speaker in conversation.speakers}
        findings = []
        for result in results:
            if result.status in {VerificationStatus.SUPPORTED, VerificationStatus.VERIFIED}:
                continue
            severity = {
                VerificationStatus.FALSE: 5,
                VerificationStatus.CONTRADICTED: 3,
                VerificationStatus.MISLEADING: 2,
                VerificationStatus.UNVERIFIED: 1,
            }.get(result.status, 1)
            findings.append(
                Finding(
                    type=FindingType.FACTUAL_VERIFICATION,
                    status=result.status,
                    severity=severity,
                    confidence=result.confidence,
                    speaker=speaker_labels.get(result.claim.speaker_id or "", result.claim.speaker_id),
                    original_statement=result.claim.original_statement,
                    explanation=result.explanation,
                    evidence=result.evidence,
                    context=result.claim.surrounding_context,
                    limitations=result.limitations,
                )
            )
        return findings

    @staticmethod
    def _deduplicate(findings: list[Finding]) -> list[Finding]:
        seen: set[tuple[str, str, str | None]] = set()
        unique: list[Finding] = []
        for finding in findings:
            key = (
                str(finding.type),
                finding.original_statement.casefold().strip(),
                finding.related_statement.casefold().strip() if finding.related_statement else None,
            )
            if key not in seen:
                seen.add(key)
                unique.append(finding)
        return unique

    @staticmethod
    def _summary(
        message_count: int,
        claim_count: int,
        findings: list[Finding],
        status_counts: Counter,
    ) -> str:
        unverified = status_counts.get(VerificationStatus.UNVERIFIED, 0)
        return (
            f"Analyzed {message_count} messages and extracted {claim_count} factual claims. "
            f"Found {len(findings)} review items; {unverified} claim(s) remain unverified. "
            "An unverified claim is not a false claim, and the report does not assess speaker intent."
        )
