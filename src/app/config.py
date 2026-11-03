"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ProviderName = Literal["none", "openai", "anthropic", "local"]


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = float(raw)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _nonnegative_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    provider: ProviderName = "none"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-haiku-latest"
    local_base_url: str = "http://localhost:11434/v1"
    local_model: str = "qwen2.5:7b"
    timeout_seconds: float = 30.0
    max_retries: int = 2
    external_verification_enabled: bool = False
    external_verification_endpoint: str | None = None
    external_verification_api_key: str | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        _load_project_env_file()
        provider = os.getenv("VERITAS_PROVIDER", "none").strip().lower()
        if provider not in {"none", "openai", "anthropic", "local"}:
            raise ValueError("VERITAS_PROVIDER must be none, openai, anthropic, or local")
        external_enabled = os.getenv("VERITAS_EXTERNAL_VERIFICATION_ENABLED", "false").lower()
        return cls(
            provider=provider,  # type: ignore[arg-type]
            openai_api_key=os.getenv("VERITAS_OPENAI_API_KEY") or None,
            openai_model=os.getenv("VERITAS_OPENAI_MODEL", "gpt-4o-mini"),
            anthropic_api_key=os.getenv("VERITAS_ANTHROPIC_API_KEY") or None,
            anthropic_model=os.getenv("VERITAS_ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            local_base_url=os.getenv("VERITAS_LOCAL_BASE_URL", "http://localhost:11434/v1"),
            local_model=os.getenv("VERITAS_LOCAL_MODEL", "qwen2.5:7b"),
            timeout_seconds=_positive_float("VERITAS_TIMEOUT_SECONDS", 30.0),
            max_retries=_nonnegative_int("VERITAS_MAX_RETRIES", 2),
            external_verification_enabled=external_enabled in {"1", "true", "yes", "on"},
            external_verification_endpoint=os.getenv("VERITAS_EXTERNAL_VERIFICATION_ENDPOINT") or None,
            external_verification_api_key=os.getenv("VERITAS_EXTERNAL_VERIFICATION_API_KEY") or None,
        )


def _load_project_env_file(path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries without overriding process environment."""
    env_file = path or Path.cwd() / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip().strip("\"'")
        os.environ.setdefault(key.strip(), value)


def create_provider(settings: Settings):
    """Construct the selected provider, or return ``None`` for offline mode."""
    if settings.provider == "none":
        return None
    if settings.provider == "openai":
        from app.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            timeout=settings.timeout_seconds,
            max_retries=settings.max_retries,
        )
    if settings.provider == "anthropic":
        from app.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            timeout=settings.timeout_seconds,
            max_retries=settings.max_retries,
        )
    from app.providers.local_provider import LocalProvider

    return LocalProvider(
        model=settings.local_model,
        base_url=settings.local_base_url,
        timeout=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )


def create_evidence_provider(settings: Settings):
    """Create the configured JSON evidence adapter when explicitly enabled."""
    if not settings.external_verification_enabled:
        return None
    if not settings.external_verification_endpoint:
        raise ValueError(
            "External verification is enabled but VERITAS_EXTERNAL_VERIFICATION_ENDPOINT is empty"
        )
    from app.providers.evidence import ConfiguredJsonEvidenceProvider

    return ConfiguredJsonEvidenceProvider(
        endpoint=settings.external_verification_endpoint,
        api_key=settings.external_verification_api_key,
        timeout=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )
