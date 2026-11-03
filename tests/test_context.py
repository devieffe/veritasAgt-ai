from app.core.models import (
    Evidence,
    EvidenceSourceType,
    Finding,
    FindingType,
    VerificationStatus,
)
from app.core.parser import ConversationParser
from app.engines.context_analysis import ContextAnalysisEngine


def test_context_review_removes_a_finding_resolved_by_correction() -> None:
    conversation = ConversationParser().parse(
        "Speaker A: The jar is full right now.\nSpeaker A: Correction: the jar is empty right now."
    )
    finding = Finding(
        type=FindingType.CONTRADICTION,
        status=VerificationStatus.CONTRADICTED,
        severity=3,
        confidence=80,
        original_statement=conversation.messages[0].text,
        related_statement=conversation.messages[1].text,
        explanation="The statements differ.",
        evidence=[
            Evidence(
                source_type=EvidenceSourceType.CONVERSATION,
                source_reference=message.id,
                relevant_content=message.text,
                reliability_assessment="Transcript only.",
            )
            for message in conversation.messages
        ],
    )

    result = ContextAnalysisEngine().analyze(conversation, [finding])

    assert result.findings == []
    assert any("correction" in item.casefold() for item in result.limitations)


def test_context_review_keeps_temporally_distinct_statements_separate() -> None:
    conversation = ConversationParser().parse(
        "Speaker A: The jar is full today.\nSpeaker B: The jar was empty yesterday."
    )
    finding = Finding(
        type=FindingType.CONTRADICTION,
        status=VerificationStatus.CONTRADICTED,
        severity=3,
        confidence=80,
        original_statement=conversation.messages[0].text,
        related_statement=conversation.messages[1].text,
        explanation="The statements differ.",
        evidence=[
            Evidence(
                source_type=EvidenceSourceType.CONVERSATION,
                source_reference=message.id,
                relevant_content=message.text,
                reliability_assessment="Transcript only.",
            )
            for message in conversation.messages
        ],
    )

    result = ContextAnalysisEngine().analyze(conversation, [finding])

    assert result.findings == []
    assert any("different explicit time periods" in item for item in result.limitations)
