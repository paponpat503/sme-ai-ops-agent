from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx
from dotenv import load_dotenv
from app.config import get_settings
from app.resilience import CircuitBreaker, CircuitOpenError, RetryPolicy, call_with_retry

load_dotenv()


@dataclass(frozen=True)
class LLMResult:
    provider: str
    text: str
    available: bool
    error: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0


_OPENAI_BREAKER = CircuitBreaker()


class LLMProvider(Protocol):
    name: str

    def is_configured(self) -> bool:
        """Return True when the provider has the minimum local configuration."""

    def generate(self, prompt: str) -> LLMResult:
        """Generate text for a prompt."""


class UnavailableProvider:
    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason

    def is_configured(self) -> bool:
        return False

    def generate(self, prompt: str) -> LLMResult:
        return LLMResult(provider=self.name, text="", available=False, error=self.reason)


class FutureProvider:
    """Placeholder adapter for provider-specific implementations.

    The interface is intentionally real, but the implementation avoids live API
    calls until a production adapter is added.
    """

    def __init__(self, name: str, api_key_env: str) -> None:
        self.name = name
        self.api_key_env = api_key_env

    def is_configured(self) -> bool:
        return bool(os.getenv(self.api_key_env))

    def generate(self, prompt: str) -> LLMResult:
        if not self.is_configured():
            return LLMResult(
                provider=self.name,
                text="",
                available=False,
                error=f"{self.api_key_env} is not configured.",
            )
        return LLMResult(
            provider=self.name,
            text="",
            available=False,
            error=f"{self.name} adapter is configured but not implemented yet.",
        )


class OpenAIProvider:
    name = "openai"

    def __init__(self) -> None:
        self.api_key_env = "OPENAI_API_KEY"
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))

    def is_configured(self) -> bool:
        return bool(os.getenv(self.api_key_env))

    def generate(self, prompt: str) -> LLMResult:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            return LLMResult(
                provider=self.name,
                text="",
                available=False,
                error=f"{self.api_key_env} is not configured.",
            )

        payload = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You are a B2B operations agent. Return valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        settings = get_settings()
        _OPENAI_BREAKER.failure_threshold = settings.circuit_failure_threshold
        _OPENAI_BREAKER.cooldown_seconds = settings.circuit_cooldown_seconds

        def request() -> httpx.Response:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            response.raise_for_status()
            return response

        try:
            response = call_with_retry(
                request,
                policy=RetryPolicy(max_retries=settings.provider_max_retries),
                breaker=_OPENAI_BREAKER,
                is_retryable=_is_retryable_http_error,
            )
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            if not text:
                return LLMResult(
                    provider=self.name,
                    text="",
                    available=False,
                    error="OpenAI returned an empty message.",
                )
            usage = data.get("usage", {})
            prompt_tokens = int(usage.get("prompt_tokens", 0))
            completion_tokens = int(usage.get("completion_tokens", 0))
            return LLMResult(
                provider=self.name,
                text=text,
                available=True,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_usd=round(
                    prompt_tokens * settings.llm_input_cost_per_million / 1_000_000
                    + completion_tokens * settings.llm_output_cost_per_million / 1_000_000,
                    8,
                ),
            )
        except (httpx.HTTPError, CircuitOpenError, KeyError, IndexError, ValueError) as exc:
            return LLMResult(
                provider=self.name,
                text="",
                available=False,
                error=f"OpenAI request failed: {exc}",
            )


def _is_retryable_http_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    provider_name = (provider_name or os.getenv("LLM_PROVIDER", "")).strip().lower()
    if not provider_name:
        provider_name = "openai"

    providers: dict[str, LLMProvider] = {
        "openai": OpenAIProvider(),
        "anthropic": FutureProvider("anthropic", "ANTHROPIC_API_KEY"),
        "gemini": FutureProvider("gemini", "GEMINI_API_KEY"),
    }
    return providers.get(
        provider_name,
        UnavailableProvider(provider_name, f"Unsupported LLM_PROVIDER: {provider_name}."),
    )
