from app.core.parser import ConversationParser
from app.engines.nonsense_detection import NonsenseDetectionEngine


def test_absurd_cause_is_distinct_from_unlikely_factual_claim_and_metaphor() -> None:
    conversation = ConversationParser().parse(
        "Speaker A: If it rains tomorrow, the sun will cease to exist.\n"
        "Speaker B: Drinking one glass of water increases weight by ten kilograms.\n"
        "Speaker A: A quiet evening is a blanket over the city."
    )

    findings = NonsenseDetectionEngine().detect(conversation)

    assert len(findings) == 1
    assert findings[0].original_statement == "If it rains tomorrow, the sun will cease to exist."
    assert findings[0].type == "nonsense"
