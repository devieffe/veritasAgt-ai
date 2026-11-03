from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.models import AnalysisReport, Finding, FindingType, VerificationStatus
from app.core.orchestrator import AnalysisOrchestrator


def test_representative_conversation_runs_through_complete_pipeline() -> None:
    fixture = Path(__file__).parent / "fixtures" / "representative_conversation.txt"
    text = fixture.read_text(encoding="utf-8")

    report = AnalysisOrchestrator().analyze_conversation(text)

    finding_types = {finding.type for finding in report.findings}
    assert {
        FindingType.CONTRADICTION,
        FindingType.FACTUAL_VERIFICATION,
        FindingType.MISREPRESENTATION,
        FindingType.NONSENSE,
        FindingType.LOGICAL_FALLACY,
    } <= finding_types
    assert any(claim.original_statement.startswith("Drinking one glass") for claim in report.extracted_claims)
    assert any(
        finding.status == VerificationStatus.UNVERIFIED
        and finding.original_statement.startswith("Drinking one glass")
        for finding in report.findings
    )
    assert all(0 <= finding.severity <= 5 for finding in report.findings)
    assert all(0 <= finding.confidence <= 100 for finding in report.findings)
    assert "intent" in report.overall_summary
    assert report.analysis_limitations
    assert AnalysisReport.model_validate_json(report.model_dump_json())


def test_finding_rejects_out_of_range_severity_and_confidence() -> None:
    with pytest.raises(ValidationError):
        Finding(
            type=FindingType.FACTUAL_VERIFICATION,
            severity=6,
            confidence=50,
            original_statement="A statement.",
            explanation="Test validation.",
        )
    with pytest.raises(ValidationError):
        Finding(
            type=FindingType.FACTUAL_VERIFICATION,
            severity=3,
            confidence=101,
            original_statement="A statement.",
            explanation="Test validation.",
        )
