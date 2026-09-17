from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.providers import llmaas
from app.providers.llmaas import LLMAASError, LLMAASProvider, _normalize_json_response


def configured_settings() -> Settings:
    return Settings(
        llm_api_key=SecretStr("api-client-key"),
        llmaas_client_id="oauth-client",
        llmaas_client_secret=SecretStr("oauth-secret"),
    )


def test_json_response_normalization_accepts_plain_or_fenced_json_only():
    assert _normalize_json_response(' {"requirements": []} ') == '{"requirements": []}'
    assert _normalize_json_response('```json\n{"requirements": []}\n```') == '{"requirements": []}'
    assert _normalize_json_response('Here is JSON:\n{"requirements": []}') == 'Here is JSON:\n{"requirements": []}'


@pytest.mark.asyncio
async def test_provider_uses_oauth_token_and_api_client_header(monkeypatch):
    token_calls = 0
    captured: dict[str, object] = {}

    class FakeHttpClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, data):
            nonlocal token_calls
            token_calls += 1
            assert data["client_secret"] == "oauth-secret"
            return httpx.Response(200, json={"access_token": "oauth-token", "expires_in": 300}, request=httpx.Request("POST", url))

    class FakeCompletions:
        @property
        def with_raw_response(self): return self
        async def create(self, **kwargs):
            captured["chat"] = kwargs
            response = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))],
                usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4),
            )
            return SimpleNamespace(parse=lambda: response, headers={"x-ratelimit-remaining-tokens": "9,984"})

    class FakeEmbeddings:
        @property
        def with_raw_response(self): return self
        async def create(self, **kwargs):
            captured["embedding"] = kwargs
            response = SimpleNamespace(
                data=[SimpleNamespace(index=0, embedding=[0.1, 0.2])],
                usage=SimpleNamespace(prompt_tokens=3, completion_tokens=0),
            )
            return SimpleNamespace(parse=lambda: response, headers={"x-ratelimit-remaining-tokens": "9981"})

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())
            self.embeddings = FakeEmbeddings()

    monkeypatch.setattr(llmaas.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(llmaas, "AsyncOpenAI", FakeOpenAI)
    provider = LLMAASProvider(configured_settings())

    assert await provider.generate_text("hello", "system") == "answer"
    assert await provider.embed(["text"]) == [[0.1, 0.2]]
    assert token_calls == 1
    assert captured["client"]["api_key"] == "oauth-token"
    assert captured["client"]["default_headers"] == {"X-LLM-API-CLIENT-ID": "Bearer api-client-key"}
    assert captured["chat"]["response_format"] == {"type": "json_object"}
    assert provider.usage.input_tokens == 15
    assert provider.usage.output_tokens == 4
    assert provider.usage.total_tokens == 19
    assert provider.usage.remaining_tokens == 9981


@pytest.mark.asyncio
async def test_provider_redacts_authentication_failure(monkeypatch):
    class FailingHttpClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, data):
            raise httpx.ConnectError("response contains sensitive details")

    monkeypatch.setattr(llmaas.httpx, "AsyncClient", FailingHttpClient)
    provider = LLMAASProvider(configured_settings())
    with pytest.raises(LLMAASError, match="authentication failed") as failure:
        await provider.generate_text("hello")
    assert "sensitive" not in str(failure.value)