from app.core.models import Evidence, EvidenceSourceType, VerificationStatus
from app.core.parser import ConversationParser
from app.engines.claim_extraction import ClaimExtractionEngine
from app.engines.factual_verification import FactualVerificationEngine


def test_no_source_means_unverified_not_false() -> None:
    conversation = ConversationParser().parse("Speaker A: Drinking water increases weight by ten kilograms.")
    claim = ClaimExtractionEngine().extract_claims(conversation)[0]

    result = FactualVerificationEngine().verify(claim)

    assert result.status == VerificationStatus.UNVERIFIED
    assert result.status != VerificationStatus.FALSE
    assert "does not mean FALSE" in result.limitations[0]


def test_supplied_matching_evidence_is_retained() -> None:
    conversation = ConversationParser().parse("Speaker A: The jar holds four liters.")
    claim = ClaimExtractionEngine().extract_claims(conversation)[0]
    source = Evidence(
        source_type=EvidenceSourceType.USER_DOCUMENT,
        source_reference="notes.txt",
        relevant_content="The jar holds four liters according to the measurement note.",
        reliability_assessment="User-provided measurement note.",
    )

    result = FactualVerificationEngine().verify(claim, evidence=[source])

    assert result.status == VerificationStatus.SUPPORTED
    assert result.evidence == [source]


def test_conflicting_conversation_statement_does_not_prove_which_is_true() -> None:
    conversation = ConversationParser().parse(
        "Speaker A: The jar is full right now.\nSpeaker B: The jar is empty right now."
    )
    claims = ClaimExtractionEngine().extract_claims(conversation)

    result = FactualVerificationEngine().verify(claims[0], conversation=conversation)

    assert result.status == VerificationStatus.CONTRADICTED
    assert result.status != VerificationStatus.FALSE
    assert result.evidence[0].source_type == EvidenceSourceType.CONVERSATION
