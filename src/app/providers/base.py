"""Provider contract and common structured-response handling."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class ProviderError(RuntimeError):
    """Raised when a configured model provider cannot complete a request."""


class LLMProvider(ABC):
    """Provider-neutral interface; engines never depend on vendor SDKs."""

    @abstractmethod
    def generate_response(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        """Generate text from a user prompt."""

    def analyze_structured(
        self,
        prompt: str,
        response_model: type[T],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> T:
        """Request and validate one JSON object against a Pydantic schema."""
        schema = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        instructions = (
            f"{prompt}\n\nReturn one JSON object matching this JSON schema. "
            f"Do not include markdown fences.\n{schema}"
        )
        raw = self.generate_response(
            instructions,
            system_prompt=system_prompt or "Return valid structured JSON only.",
            temperature=temperature,
        )
        decoder = json.JSONDecoder()
        start = raw.find("{")
        if start < 0:
            raise ProviderError("The provider returned no JSON object")
        try:
            payload, _ = decoder.raw_decode(raw[start:])
            return response_model.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            raise ProviderError("The provider response did not match the requested schema") from error
