"""Validated domain models shared by the engines and CLI."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClaimCategory(StrEnum):
    FACTUAL = "factual"
    OPINION = "opinion"
    QUESTION = "question"
    HYPOTHETICAL = "hypothetical"
    JOKE = "joke"
    METAPHOR = "metaphor"
    SPECULATION = "speculation"
    CREATIVE = "creative"


class FindingType(StrEnum):
    CONTRADICTION = "contradiction"
    FACTUAL_VERIFICATION = "factual_verification"
    MISREPRESENTATION = "misrepresentation"
    NONSENSE = "nonsense"
    LOGICAL_FALLACY = "logical_fallacy"
    CONTEXT = "context"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvidenceSourceType(StrEnum):
    CONVERSATION = "conversation"
    USER_DOCUMENT = "user_document"
    EXTERNAL_SOURCE = "external_source"
    CONFIGURED_API = "configured_api"
    UNKNOWN = "unknown"


class DomainModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)


class Speaker(DomainModel):
    id: str
    label: str


class Message(DomainModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    speaker_id: str | None = None
    timestamp: datetime | None = None
    order: int = Field(ge=0)


class Conversation(DomainModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    messages: list[Message]
    speakers: list[Speaker] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_unique_message_ids(self) -> "Conversation":
        message_ids = [message.id for message in self.messages]
        if len(message_ids) != len(set(message_ids)):
            raise ValueError("Message identifiers must be unique within a conversation")
        return self


class Claim(DomainModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    original_statement: str
    speaker_id: str | None = None
    message_id: str
    category: ClaimCategory = ClaimCategory.FACTUAL
    surrounding_context: str = ""
    extraction_confidence: float = Field(ge=0, le=100)


class Evidence(DomainModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_type: EvidenceSourceType
    source_reference: str | None = None
    relevant_content: str
    reliability_assessment: str
    retrieval_information: dict[str, Any] = Field(default_factory=dict)


class Finding(DomainModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: FindingType
    status: VerificationStatus = VerificationStatus.NOT_APPLICABLE
    severity: int = Field(ge=0, le=5)
    confidence: float = Field(ge=0, le=100)
    speaker: str | None = None
    original_statement: str
    related_statement: str | None = None
    explanation: str
    evidence: list[Evidence] = Field(default_factory=list)
    context: str = ""
    limitations: list[str] = Field(default_factory=list)


class AnalysisReport(DomainModel):
    original_conversation_reference: str
    extracted_claims: list[Claim] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    overall_summary: str
    processing_metadata: dict[str, Any] = Field(default_factory=dict)
    analysis_limitations: list[str] = Field(default_factory=list)


class VerificationResult(DomainModel):
    claim: Claim
    status: VerificationStatus
    evidence: list[Evidence] = Field(default_factory=list)
    explanation: str
    confidence: float = Field(ge=0, le=100)
    limitations: list[str] = Field(default_factory=list)


class EvaluationResult(DomainModel):
    dataset_name: str
    sample_count: int = Field(ge=0)
    category_metrics: dict[str, dict[str, float | int]] = Field(default_factory=dict)
    overall_metrics: dict[str, float | int] = Field(default_factory=dict)
    whileai_metrics: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
