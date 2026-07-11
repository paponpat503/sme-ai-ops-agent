import json

import httpx

from app.config import get_settings
from app.llm import providers


class FakeClient:
    attempts = 0
    def __init__(self, timeout):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def post(self, url, headers, json):
        FakeClient.attempts += 1
        request = httpx.Request("POST", url)
        if FakeClient.attempts == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": '{"ok":true}'}}], "usage": {"prompt_tokens": 1000, "completion_tokens": 500}},
        )


def test_provider_retries_and_accounts_for_cost(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("PROVIDER_MAX_RETRIES", "1")
    monkeypatch.setenv("LLM_INPUT_COST_PER_MILLION", "2")
    monkeypatch.setenv("LLM_OUTPUT_COST_PER_MILLION", "4")
    get_settings.cache_clear()
    FakeClient.attempts = 0
    providers._OPENAI_BREAKER.record_success()
    monkeypatch.setattr(providers.httpx, "Client", FakeClient)
    result = providers.OpenAIProvider().generate("prompt")
    assert result.available
    assert FakeClient.attempts == 2
    assert result.prompt_tokens == 1000
    assert result.completion_tokens == 500
    assert result.estimated_cost_usd == 0.004
    get_settings.cache_clear()
