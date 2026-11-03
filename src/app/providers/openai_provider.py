"""OpenAI chat-completions adapter with lazy optional dependency loading."""

from __future__ import annotations

import os

from app.providers.base import LLMProvider, ProviderError


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ProviderError("OpenAI was selected but no API key is configured")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise ProviderError("Install the optional 'providers' extra to use OpenAI") from error
        self.model = model
        self.client = OpenAI(api_key=key, timeout=timeout, max_retries=max_retries)

    def generate_response(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except Exception as error:
            raise ProviderError("OpenAI request failed; check the model, network, and credentials") from error
        content = response.choices[0].message.content
        if not content:
            raise ProviderError("OpenAI returned an empty response")
        return content
