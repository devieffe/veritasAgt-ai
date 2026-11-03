from app.core.parser import ConversationParser
from app.engines.misrepresentation import MisrepresentationDetectionEngine


def test_flags_unsupported_absolute_scope_without_claiming_intent() -> None:
    conversation = ConversationParser().parse("Speaker A: Everyone always agrees with this conclusion.")

    findings = MisrepresentationDetectionEngine().detect(conversation)

    assert len(findings) == 1
    assert "unsupported_generalization" in findings[0].explanation
    assert "intent" in findings[0].explanation
    assert findings[0].speaker == "Speaker A"
