from __future__ import annotations

import os
import json
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator


Role = Literal["viewer", "operator", "admin"]


class ApiIdentity(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=80)
    user_id: str = Field(min_length=1, max_length=120)
    roles: set[Role] = Field(min_length=1)


class Settings(BaseModel):
    app_env: Literal["local", "test", "production"] = "local"
    agent_mode: Literal["deterministic", "llm", "auto", "tool_agent"] = "auto"
    tool_transport: Literal["local", "mcp"] = "local"
    retriever_mode: Literal["tfidf", "pgvector", "hybrid"] = "tfidf"
    api_key: str | None = None
    api_keys: dict[str, ApiIdentity] = Field(default_factory=dict)
    database_url: str | None = None
    demo_tenant_id: str = "demo"
    max_tool_calls: int = Field(default=5, ge=1, le=10)
    request_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    provider_max_retries: int = Field(default=2, ge=0, le=5)
    circuit_failure_threshold: int = Field(default=3, ge=1, le=20)
    circuit_cooldown_seconds: float = Field(default=30.0, ge=1, le=600)
    rate_limit_requests: int = Field(default=60, ge=1, le=10_000)
    rate_limit_window_seconds: float = Field(default=60.0, ge=1, le=3600)
    rate_limit_max_clients: int = Field(default=10_000, ge=100, le=100_000)
    max_request_body_bytes: int = Field(default=64_000, ge=1024, le=10_000_000)
    trust_proxy_headers: bool = False
    retrieval_min_score: float = Field(default=0.12, ge=0, le=1)
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = Field(default=1536, ge=1, le=4096)
    llm_input_cost_per_million: float = Field(default=0.0, ge=0)
    llm_output_cost_per_million: float = Field(default=0.0, ge=0)
    log_level: str = "INFO"

    @field_validator("api_key", mode="before")
    @classmethod
    def empty_key_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @classmethod
    def from_env(cls) -> "Settings":
        raw_api_keys = os.getenv("APP_API_KEYS_JSON", "{}").strip() or "{}"
        return cls(
            app_env=os.getenv("APP_ENV", "local").strip().lower(),
            agent_mode=os.getenv("AGENT_MODE", "auto").strip().lower(),
            tool_transport=os.getenv("TOOL_TRANSPORT", "local").strip().lower(),
            retriever_mode=os.getenv("RETRIEVER_MODE", "tfidf").strip().lower(),
            api_key=os.getenv("APP_API_KEY"),
            api_keys=json.loads(raw_api_keys),
            database_url=os.getenv("DATABASE_URL") or None,
            demo_tenant_id=os.getenv("DEMO_TENANT_ID", "demo").strip(),
            max_tool_calls=os.getenv("MAX_TOOL_CALLS", "5"),
            request_timeout_seconds=os.getenv("REQUEST_TIMEOUT_SECONDS", "30"),
            provider_max_retries=os.getenv("PROVIDER_MAX_RETRIES", "2"),
            circuit_failure_threshold=os.getenv("CIRCUIT_FAILURE_THRESHOLD", "3"),
            circuit_cooldown_seconds=os.getenv("CIRCUIT_COOLDOWN_SECONDS", "30"),
            rate_limit_requests=os.getenv("RATE_LIMIT_REQUESTS", "60"),
            rate_limit_window_seconds=os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"),
            rate_limit_max_clients=os.getenv("RATE_LIMIT_MAX_CLIENTS", "10000"),
            max_request_body_bytes=os.getenv("MAX_REQUEST_BODY_BYTES", "64000"),
            trust_proxy_headers=os.getenv("TRUST_PROXY_HEADERS", "false").strip().lower() in {"1", "true", "yes"},
            retrieval_min_score=os.getenv("RETRIEVAL_MIN_SCORE", "0.12"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small").strip(),
            embedding_dimensions=os.getenv("EMBEDDING_DIMENSIONS", "1536"),
            llm_input_cost_per_million=os.getenv("LLM_INPUT_COST_PER_MILLION", "0"),
            llm_output_cost_per_million=os.getenv("LLM_OUTPUT_COST_PER_MILLION", "0"),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def validate_production_settings(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.app_env == "production" and not settings.api_key and not settings.api_keys:
        raise RuntimeError("APP_API_KEY or APP_API_KEYS_JSON is required when APP_ENV=production.")
