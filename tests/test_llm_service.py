from __future__ import annotations

from app.core.config import Settings
from app.services.llm_service import LLMService


class _FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict[str, object]:
        return self._body


def test_llm_service_default_uses_env_runtime_when_credentials_exist(monkeypatch) -> None:
    captured_payload: dict[str, object] = {}

    def _fake_post(url, headers, json, timeout):  # noqa: ANN001
        captured_payload["url"] = url
        captured_payload["headers"] = headers
        captured_payload["json"] = json
        captured_payload["timeout"] = timeout
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "real-chat-answer",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.services.llm_service.httpx.post", _fake_post)

    settings = Settings(
        llm_provider="mock",
        llm_base_url="https://api.openai.com/v1",
        llm_api_key="sk-test",
        llm_model="gpt-4.1-mini",
    )
    service = LLMService(settings=settings)

    answer = service.answer_chat("hello")
    assert answer == "real-chat-answer"
    assert captured_payload["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured_payload["json"] == {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": "You are CaiBao, a helpful enterprise assistant."},
            {"role": "user", "content": "hello"},
        ],
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
