"""Anthropic Messages API adapter with lazy optional dependency loading."""

from __future__ import annotations

import os

from app.providers.base import LLMProvider, ProviderError


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ProviderError("Anthropic was selected but no API key is configured")
        try:
            from anthropic import Anthropic
        except ImportError as error:
            raise ProviderError("Install the optional 'providers' extra to use Anthropic") from error
        self.model = model
        self.client = Anthropic(api_key=key, timeout=timeout, max_retries=max_retries)

    def generate_response(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt or "Return valid structured JSON only.",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
        except Exception as error:
            raise ProviderError("Anthropic request failed; check the model, network, and credentials") from error
        content = "\n".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        if not content:
            raise ProviderError("Anthropic returned an empty response")
        return content
