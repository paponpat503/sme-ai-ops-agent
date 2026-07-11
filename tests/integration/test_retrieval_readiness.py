import pytest

from app.config import get_settings
from app.rag.runtime import RetrieverRuntime


def test_vector_configuration_failure_abstains_and_fails_readiness(monkeypatch):
    monkeypatch.setenv("RETRIEVER_MODE", "hybrid")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    runtime = RetrieverRuntime()
    try:
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            runtime.build()
        assert runtime.is_ready() is False
        assert runtime.search("refund policy") == []
    finally:
        get_settings.cache_clear()
