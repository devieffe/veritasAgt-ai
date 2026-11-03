from app.core.parser import ConversationParser
from app.engines.claim_extraction import ClaimExtractionEngine


def test_claims_preserve_exact_words_and_skip_nonfactual_language() -> None:
    conversation = ConversationParser().parse(
        "Speaker A: The container holds four liters.\n"
        "Speaker B: I think this is useful.\n"
        "Speaker A: If the lid is open, it might spill.\n"
        "Speaker B: A quiet evening is a blanket over the city.\n"
        "Speaker A: Could the container hold more?"
    )

    claims = ClaimExtractionEngine().extract_claims(conversation)

    assert [claim.original_statement for claim in claims] == ["The container holds four liters."]
    assert claims[0].message_id == conversation.messages[0].id
    assert claims[0].speaker_id == "Speaker A"
    assert claims[0].extraction_confidence <= 100


def test_claim_extraction_does_not_remove_original_punctuation() -> None:
    conversation = ConversationParser().parse("Speaker A: The jar contains 2.5 liters!")

    claim = ClaimExtractionEngine().extract_claims(conversation)[0]

    assert claim.original_statement == "The jar contains 2.5 liters!"
