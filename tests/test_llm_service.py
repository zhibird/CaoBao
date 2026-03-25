from __future__ import annotations

import httpx

from app.core.config import Settings
from app.services.llm_service import LLMService, VisionAttachment


class _FakeResponse:
    def __init__(self, body: dict[str, object], status_code: int = 200) -> None:
        self._body = body
        self.status_code = status_code
        self.text = str(body)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
            response = httpx.Response(self.status_code, request=request, json=self._body)
            raise httpx.HTTPStatusError("request failed", request=request, response=response)
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


def test_llm_service_sends_multimodal_payload_when_images_are_provided(monkeypatch) -> None:
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
                            "content": "vision-answer",
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

    answer = service.answer_chat(
        "请描述图片内容",
        image_attachments=[
            VisionAttachment(
                document_id="doc-1",
                source_name="receipt.png",
                mime_type="image/png",
                data_url="data:image/png;base64,AAAA",
            )
        ],
    )
    assert answer == "vision-answer"

    user_message = captured_payload["json"]["messages"][1]  # type: ignore[index]
    assert user_message["role"] == "user"
    assert isinstance(user_message["content"], list)
    assert user_message["content"][0] == {"type": "text", "text": "请描述图片内容"}
    assert user_message["content"][1] == {
        "type": "image_url",
        "image_url": {
            "url": "data:image/png;base64,AAAA",
            "detail": "auto",
        },
    }


def test_llm_service_falls_back_to_text_when_vision_is_rejected(monkeypatch) -> None:
    captured_payloads: list[dict[str, object]] = []
    call_count = {"count": 0}

    def _fake_post(url, headers, json, timeout):  # noqa: ANN001
        captured_payloads.append(json)
        call_count["count"] += 1
        if call_count["count"] == 1:
            return _FakeResponse(
                {"error": {"message": "This model does not support image inputs."}},
                status_code=400,
            )
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "fallback-answer",
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

    answer = service.answer_chat(
        "请读取这张图片",
        image_attachments=[
            VisionAttachment(
                document_id="doc-2",
                source_name="invoice.png",
                mime_type="image/png",
                data_url="data:image/png;base64,BBBB",
            )
        ],
        fallback_text_context="[invoice.png]\nOCR result",
    )
    assert answer == "fallback-answer"
    assert len(captured_payloads) == 2
    assert isinstance(captured_payloads[0]["messages"][1]["content"], list)  # type: ignore[index]
    assert captured_payloads[1]["messages"][1]["content"] == "请读取这张图片\n\nAttachment text fallback:\n[invoice.png]\nOCR result"  # type: ignore[index]
