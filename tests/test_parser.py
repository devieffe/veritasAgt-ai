from app.core.parser import ConversationParser


def test_parser_preserves_explicit_labels_text_and_order() -> None:
    raw = "Speaker A: The jar is full.\nSpeaker B: It is empty."

    conversation = ConversationParser().parse(raw)

    assert [message.speaker_id for message in conversation.messages] == ["Speaker A", "Speaker B"]
    assert [message.order for message in conversation.messages] == [0, 1]
    assert [message.text for message in conversation.messages] == ["The jar is full.", "It is empty."]
    assert {speaker.label for speaker in conversation.speakers} == {"Speaker A", "Speaker B"}


def test_unlabelled_blocks_remain_unlabelled() -> None:
    conversation = ConversationParser().parse("The jar is full.\n\nIt is empty.")

    assert len(conversation.messages) == 2
    assert all(message.speaker_id is None for message in conversation.messages)


def test_parser_keeps_multilingual_wording_and_sentence_punctuation() -> None:
    parser = ConversationParser()
    conversation = parser.parse("Speaker A: Ça fonctionne.\nSpeaker B: Это неверно?")

    assert [message.text for message in conversation.messages] == ["Ça fonctionne.", "Это неверно?"]
    assert parser.split_sentences("Это верно? כן.") == ["Это верно?", "כן."]
