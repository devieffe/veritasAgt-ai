from app.core.parser import ConversationParser
from app.engines.logical_coherence import LogicalCoherenceEngine


def test_explains_unsupported_causal_inference() -> None:
    conversation = ConversationParser().parse(
        "Speaker A: The garden grew this week, so the new lamp caused all plant growth."
    )

    findings = LogicalCoherenceEngine().analyze(conversation)

    assert len(findings) == 1
    assert "unsupported_causal_inference" in findings[0].explanation
    assert "without showing a causal link" in findings[0].explanation


def test_neutral_statement_does_not_receive_a_fallacy_label() -> None:
    conversation = ConversationParser().parse("Speaker A: The jar is on the table.")

    assert LogicalCoherenceEngine().analyze(conversation) == []
