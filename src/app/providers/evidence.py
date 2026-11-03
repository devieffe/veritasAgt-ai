"""Interfaces for caller-supplied and configured evidence sources."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen

from app.core.models import Evidence, EvidenceSourceType
from app.providers.base import ProviderError


class EvidenceProvider(ABC):
    @abstractmethod
    def search(self, query: str) -> list[Evidence]:
        """Return source-grounded evidence for a claim query."""


class ConfiguredJsonEvidenceProvider(EvidenceProvider):
    """Call a configured JSON search endpoint with a documented response contract."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str | None = None,
        timeout: float = 30,
        max_retries: int = 2,
    ) -> None:
        if not endpoint.startswith(("https://", "http://")):
            raise ValueError("The external evidence endpoint must use HTTP or HTTPS")
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    def search(self, query: str) -> list[Evidence]:
        parts = urlsplit(self.endpoint)
        query_values = dict(parse_qsl(parts.query, keep_blank_values=True))
        query_values["q"] = query
        target = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_values), parts.fragment))
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(target, headers=headers)
        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                results = payload.get("results")
                if not isinstance(results, list):
                    raise ProviderError("External evidence API must return a JSON 'results' array")
                return [
                    Evidence(
                        source_type=EvidenceSourceType.CONFIGURED_API,
                        source_reference=item.get("source_reference"),
                        relevant_content=item["relevant_content"],
                        reliability_assessment=item.get("reliability_assessment", "Not assessed by VeritasAgent."),
                        retrieval_information=item.get("retrieval_information", {}),
                    )
                    for item in results
                    if isinstance(item, dict) and isinstance(item.get("relevant_content"), str)
                ]
            except (URLError, TimeoutError, json.JSONDecodeError, KeyError) as error:
                if attempt >= self.max_retries:
                    raise ProviderError("The configured external evidence request failed") from error
                time.sleep(min(0.25 * (2**attempt), 2.0))
        return []
