"""Conservative parser for plain-text conversation transcripts."""

from __future__ import annotations

import re

from app.core.models import Conversation, Message, Speaker
from app.utils.text_processing import normalize_whitespace, split_sentences

_LABEL = re.compile(
	r"^\s*(?P<label>(?:Speaker\s+[A-Za-z0-9_-]+|User|Assistant|Agent|user\d+|[A-Za-z][A-Za-z0-9 _-]{0,30})):"
    r"\s*(?P<body>.*)$",
    re.IGNORECASE,
)


class ConversationParser:
    """Parse messages without guessing speaker identities or adding context."""

    def normalize_text(self, text: str) -> str:
        """Normalize line endings and outer whitespace, retaining interior wording."""
        return text.replace("\r\n", "\n").replace("\r", "\n").strip()

    def split_messages(self, raw_text: str) -> list[tuple[str | None, str]]:
        """Return ``(explicit label, original body)`` pairs in source order."""
        text = self.normalize_text(raw_text)
        if not text:
            return []

        messages: list[tuple[str | None, str]] = []
        for block in re.split(r"\n\s*\n", text):
            current_label: str | None = None
            current_lines: list[str] = []
            block_messages: list[tuple[str | None, str]] = []
            for line in block.splitlines():
                match = _LABEL.match(line)
                if match:
                    if current_lines:
                        body = "\n".join(current_lines).strip()
                        if body:
                            block_messages.append((current_label, body))
                    current_label = match.group("label").strip()
                    current_lines = [match.group("body")]
                else:
                    current_lines.append(line)
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    block_messages.append((current_label, body))
            messages.extend(block_messages)
        return messages

    def identify_speakers(self, raw_text: str) -> list[Speaker]:
        """Return only speaker labels written explicitly in the transcript."""

        speakers: dict[str, str] = {}
        for label, _body in self.split_messages(raw_text):
            if not label:
                continue
            key = label.strip().casefold()
            # Preserve the first-seen casing as the display label.
            speakers.setdefault(key, label.strip())
        return [Speaker(id=key, label=label) for key, label in speakers.items()]

    def split_sentences(self, text: str) -> list[str]:
        return split_sentences(text)

    def parse(self, raw_text: str) -> Conversation:
        parts = self.split_messages(raw_text)

        speakers_by_id: dict[str, str] = {}
        for label, _body in parts:
            if not label:
                continue
            key = label.strip().casefold()
            speakers_by_id.setdefault(key, label.strip())
        speakers = [Speaker(id=key, label=label) for key, label in speakers_by_id.items()]
        messages = [
            Message(text=body, speaker_id=label.strip().casefold() if label else None, order=index)
            for index, (label, body) in enumerate(parts)
        ]
        return Conversation(messages=messages, speakers=speakers)
