import httpx
import pytest
from fastapi.testclient import TestClient

from app.config.settings import LLMSettings, RuntimeSettings
from app.llm.client import LLMClientError, OpenAICompatibleLLMClient
from app.main import app


def _settings(*, retries: int = 1) -> LLMSettings:
    return LLMSettings(
        base_url="https://llm.example/v1",
        api_key="test-key",
        model="test-model",
        timeout_seconds=3,
        max_retries=retries,
    )


def test_runtime_settings_parse_deployment_cors_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "INTERVAI_CORS_ORIGINS",
        "https://intervai.example.com, https://preview.example.com/",
    )
    settings = RuntimeSettings.from_env()
    assert settings.cors_origins == (
        "https://intervai.example.com",
        "https://preview.example.com",
    )


def test_health_exposes_runtime_mode_without_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERVAI_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("INTERVAI_LLM_API_KEY", raising=False)
    monkeypatch.delenv("INTERVAI_LLM_MODEL", raising=False)

    payload = TestClient(app).get("/health").json()
    assert payload == {
        "status": "ok",
        "version": "0.6.0",
        "llmMode": "deterministic-fallback",
    }
    assert "key" not in str(payload).lower()


def test_llm_client_retries_one_transient_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        request = httpx.Request("POST", "https://llm.example/v1/chat/completions")
        if calls == 1:
            return httpx.Response(503, request=request, json={"error": "temporary"})
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": '{"question":"ok"}'}}]},
        )

    monkeypatch.setattr("app.llm.client.httpx.post", fake_post)
    result = OpenAICompatibleLLMClient(_settings(retries=1)).complete_json(
        system_prompt="system",
        user_prompt="user",
    )

    assert result == {"question": "ok"}
    assert calls == 2


def test_llm_timeout_fails_fast_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        request = httpx.Request("POST", "https://llm.example/v1/chat/completions")
        raise httpx.ReadTimeout("timeout", request=request)

    monkeypatch.setattr("app.llm.client.httpx.post", fake_post)

    with pytest.raises(LLMClientError, match="llm_request_timed_out"):
        OpenAICompatibleLLMClient(_settings(retries=2)).complete_json(
            system_prompt="system",
            user_prompt="user",
        )
    assert calls == 1


def test_llm_client_recovers_single_json_object_from_prefixed_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(*args, **kwargs):
        request = httpx.Request("POST", "https://llm.example/v1/chat/completions")
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "content": 'Here is the structured result:\n{"question":"Recovered JSON","rationale":"grounded"}'
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("app.llm.client.httpx.post", fake_post)
    result = OpenAICompatibleLLMClient(_settings(retries=0)).complete_json(
        system_prompt="system",
        user_prompt="user",
    )
    assert result["question"] == "Recovered JSON"
