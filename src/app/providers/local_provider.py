"""Adapter for a local OpenAI-compatible chat-completions endpoint."""

from __future__ import annotations

import json
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.providers.base import LLMProvider, ProviderError


class LocalProvider(LLMProvider):
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 2,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_key = api_key

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
        payload = json.dumps(
            {"model": self.model, "messages": messages, "temperature": temperature, "stream": False}
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(f"{self.base_url}/chat/completions", data=payload, headers=headers)

        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                if isinstance(content, str) and content:
                    return content
                raise ProviderError("The local provider returned an empty response")
            except (URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as error:
                if attempt >= self.max_retries:
                    raise ProviderError("Local model request failed; check the endpoint and model server") from error
                time.sleep(min(0.25 * (2**attempt), 2.0))
        raise ProviderError("Local model request failed")
