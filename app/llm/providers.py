from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class LLMResult:
    provider: str
    text: str
    available: bool
    error: str | None = None


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

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            if not text:
                return LLMResult(
                    provider=self.name,
                    text="",
                    available=False,
                    error="OpenAI returned an empty message.",
                )
            return LLMResult(provider=self.name, text=text, available=True)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            return LLMResult(
                provider=self.name,
                text="",
                available=False,
                error=f"OpenAI request failed: {exc}",
            )


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
