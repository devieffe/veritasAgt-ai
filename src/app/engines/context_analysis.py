"""Review candidate findings against the full transcript and uncertainty."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.core.models import Conversation, Finding, FindingType
from app.engines._shared import explicit_time_markers, has_correction_cue
from app.providers.base import LLMProvider
from app.utils.text_processing import tokenize


class ContextAnalysisResult(BaseModel):
    findings: list[Finding]
    limitations: list[str] = Field(default_factory=list)


class _Review(BaseModel):
    finding_id: str
    keep: bool
    explanation: str
    limitations: list[str] = Field(default_factory=list)


class _Reviews(BaseModel):
    reviews: list[_Review]


_AMBIGUOUS = re.compile(r"\b(?:it|this|that|they|them|some|many|soon|later)\b", re.I)
_STOPWORDS = {"a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "and", "or", "in", "on", "at", "now"}


class ContextAnalysisEngine:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def analyze(self, conversation: Conversation, findings: list[Finding]) -> ContextAnalysisResult:
        retained: list[Finding] = []
        limitations: list[str] = []
        messages_by_id = {message.id: message for message in conversation.messages}
        for earlier, later in zip(conversation.messages, conversation.messages[1:]):
            same_topic = self._shares_subject(earlier.text, later.text)
            if same_topic and has_correction_cue(later.text):
                limitations.append("A correction or clarification is present in the conversation context.")
            first_times = explicit_time_markers(earlier.text)
            later_times = explicit_time_markers(later.text)
            if same_topic and first_times and later_times and first_times != later_times:
                limitations.append("Adjacent statements refer to different explicit time periods.")

        for finding in findings:
            source_messages = [
                messages_by_id[evidence.source_reference]
                for evidence in finding.evidence
                if evidence.source_reference in messages_by_id
            ]
            if self._resolved_by_context(finding, source_messages):
                limitations.append(
                    f"A candidate conflict was treated as a correction or time change: {finding.original_statement}"
                )
                continue
            if _AMBIGUOUS.search(finding.original_statement):
                finding.limitations.append("Pronouns or broad quantifiers may depend on omitted context.")
            if any(word in finding.original_statement.casefold() for word in ("if ", "unless ", "assuming ")):
                finding.limitations.append("The statement may depend on a condition not captured in the transcript.")
            retained.append(finding)

        if self.provider is not None and retained:
            prompt = (
                "Review each candidate finding against the full conversation. Keep only findings supported by "
                "the context. Consider corrections, clarifications, temporal changes, ambiguity, and alternative "
                "interpretations. Do not infer intent. Return an explanation and limitations for each finding.\n"
                f"Conversation:\n{self._transcript(conversation)}\nCandidates:\n"
                + "\n".join(
                    f"{item.id}: {item.type} | {item.original_statement} | {item.related_statement or ''} | {item.explanation}"
                    for item in retained
                )
            )
            result = self.provider.analyze_structured(prompt, _Reviews)
            reviews = {item.finding_id: item for item in result.reviews}
            reviewed: list[Finding] = []
            for finding in retained:
                review = reviews.get(finding.id)
                if review is None:
                    reviewed.append(finding)
                    continue
                if not review.keep:
                    limitations.append(f"Context review removed a finding: {review.explanation}")
                    continue
                finding.explanation = f"{finding.explanation} Context review: {review.explanation}"
                finding.limitations.extend(review.limitations)
                reviewed.append(finding)
            retained = reviewed

        return ContextAnalysisResult(findings=retained, limitations=limitations)

    @staticmethod
    def _resolved_by_context(finding: Finding, messages: list) -> bool:
        if finding.type != FindingType.CONTRADICTION or len(messages) < 2:
            return False
        ordered = sorted(messages, key=lambda message: message.order)
        for earlier, later in zip(ordered, ordered[1:]):
            if has_correction_cue(later.text):
                return True
            first_times = explicit_time_markers(earlier.text)
            later_times = explicit_time_markers(later.text)
            if first_times and later_times and first_times != later_times:
                return True
        return False

    @staticmethod
    def _shares_subject(first: str, second: str) -> bool:
        first_words = {word for word in tokenize(first) if word not in _STOPWORDS and len(word) > 2}
        second_words = {word for word in tokenize(second) if word not in _STOPWORDS and len(word) > 2}
        shared = first_words & second_words
        return bool(shared)

    @staticmethod
    def _transcript(conversation: Conversation) -> str:
        return "\n".join(
            f"[{message.order}] {message.speaker_id or 'unknown'}: {message.text}"
            for message in conversation.messages
        )
