from app.core.parser import ConversationParser
from app.engines.claim_extraction import ClaimExtractionEngine
from app.engines.contradiction import ContradictionDetectionEngine


def _claims(text: str):
    conversation = ConversationParser().parse(text)
    return conversation, ClaimExtractionEngine().extract_claims(conversation)


def test_detects_direct_conflict_with_both_statements() -> None:
    conversation, claims = _claims(
        "Speaker A: The jar is full right now.\nSpeaker B: The jar is empty right now."
    )

    findings = ContradictionDetectionEngine().detect(claims, conversation)

    assert len(findings) == 1
    assert findings[0].original_statement == "The jar is full right now."
    assert findings[0].related_statement == "The jar is empty right now."
    assert len(findings[0].evidence) == 2
    assert "intent" in findings[0].explanation


def test_correction_is_not_reported_as_contradiction() -> None:
    conversation, claims = _claims(
        "Speaker A: The jar is full right now.\nSpeaker A: Correction: the jar is empty right now."
    )

    assert ContradictionDetectionEngine().detect(claims, conversation) == []


def test_time_change_and_opinion_difference_are_not_contradictions() -> None:
    parser = ConversationParser()
    engine = ContradictionDetectionEngine()

    temporal = parser.parse("Speaker A: The jar is full today.\nSpeaker B: The jar was empty yesterday.")
    temporal_claims = ClaimExtractionEngine().extract_claims(temporal)
    preferences = parser.parse("Speaker A: I think tea is pleasant.\nSpeaker B: I think tea is unpleasant.")
    preference_claims = ClaimExtractionEngine().extract_claims(preferences)

    assert engine.detect(temporal_claims, temporal) == []
    assert engine.detect(preference_claims, preferences) == []
