import base64
import time
from io import BytesIO
from uuid import uuid4

import httpx
from PIL import Image


def _create_team_user_and_conversation(client, suffix: str) -> tuple[str, str, str]:
    team_id = f"team_hist_{suffix}"
    user_id = f"u_hist_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "History Team",
            "description": "for chat history edits",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "History User",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    create_conversation = client.post(
        "/api/v1/conversations",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "title": "History Session",
        },
    )
    assert create_conversation.status_code == 201
    conversation_id = create_conversation.json()["conversation_id"]

    return team_id, user_id, conversation_id


def _build_png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (4, 4), color=(240, 240, 240)).save(output, format="PNG")
    return output.getvalue()


def _wait_document_ready(client, *, team_id: str, conversation_id: str, document_id: str, max_attempts: int = 30) -> None:
    for _ in range(max_attempts):
        response = client.get(
            f"/api/v1/documents/{document_id}",
            params={"team_id": team_id, "conversation_id": conversation_id},
        )
        assert response.status_code == 200
        status = response.json()["status"]
        if status == "ready":
            return
        assert status != "failed"
        time.sleep(0.05)
    raise AssertionError("document did not reach ready status in time")


def test_chat_echo_requires_configured_user_team(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_{suffix}"
    user_id = f"u_{suffix}"

    team_response = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Ops Team",
            "description": "for chat test",
        },
    )
    assert team_response.status_code == 201

    user_response = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Alice",
            "role": "owner",
        },
    )
    assert user_response.status_code == 201

    chat_response = client.post(
        "/api/v1/chat/echo",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "message": "hello",
        },
    )

    assert chat_response.status_code == 200
    body = chat_response.json()
    assert body["answer"] == "[Echo] hello"


def test_chat_echo_rejects_unknown_user(client) -> None:
    unknown_user_id = f"u_unknown_{uuid4().hex[:8]}"

    response = client.post(
        "/api/v1/chat/echo",
        json={
            "user_id": unknown_user_id,
            "team_id": "team_ops",
            "message": "hello",
        },
    )

    assert response.status_code == 404


def test_chat_ask_returns_answer_and_hits(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_ask_{suffix}"
    user_id = f"u_ask_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Ask Team",
            "description": "for ask test",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Operator",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "ops.md",
            "content_type": "md",
            "content": (
                "# Ops Guide\n\n"
                "Always check alerts first. "
                "Escalate incidents quickly. "
                "Keep channels updated every 10 minutes."
            ),
        },
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["document_id"]

    chunk_response = client.post(
        f"/api/v1/documents/{document_id}/chunk",
        json={
            "team_id": team_id,
            "max_chars": 100,
            "overlap": 10,
        },
    )
    assert chunk_response.status_code == 200

    index_response = client.post(
        "/api/v1/retrieval/index",
        json={
            "team_id": team_id,
            "document_id": document_id,
        },
    )
    assert index_response.status_code == 200

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "question": "alerts first?",
            "top_k": 3,
            "document_id": document_id,
        },
    )

    assert ask_response.status_code == 200
    body = ask_response.json()
    assert body["user_id"] == user_id
    assert body["team_id"] == team_id
    assert body["answer"]
    assert body["answer"].startswith("[Mock Answer]")
    assert len(body["hits"]) >= 1
    assert body["mode"] == "rag"
    assert len(body["sources"]) >= 1


def test_chat_ask_falls_back_to_chat_mode_without_index(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_ask_no_index_{suffix}"
    user_id = f"u_ask_no_index_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "NoIndex Team",
            "description": "ask without index",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Operator",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "question": "alerts first?",
            "top_k": 3,
        },
    )

    assert ask_response.status_code == 200
    body = ask_response.json()
    assert body["user_id"] == user_id
    assert body["team_id"] == team_id
    assert body["answer"]
    assert body["answer"].startswith("[Mock Chat]")
    assert body["hits"] == []
    assert body["mode"] == "chat"
    assert body["sources"] == []


def test_chat_ask_supports_selected_document_ids_and_source_snippet(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_ask_selected_{suffix}"
    user_id = f"u_ask_selected_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Selected Docs Team",
            "description": "for selected document ids",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Operator",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    alpha_doc = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "alpha.md",
            "content_type": "md",
            "content": "# Alpha\n\nAlpha runbook says check alerts first.",
        },
    )
    beta_doc = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "beta.md",
            "content_type": "md",
            "content": "# Beta\n\nBeta runbook says deploy on Friday.",
        },
    )
    assert alpha_doc.status_code == 201
    assert beta_doc.status_code == 201

    alpha_id = alpha_doc.json()["document_id"]
    beta_id = beta_doc.json()["document_id"]

    for document_id in [alpha_id, beta_id]:
        chunk_response = client.post(
            f"/api/v1/documents/{document_id}/chunk",
            json={
                "team_id": team_id,
                "max_chars": 100,
                "overlap": 10,
            },
        )
        assert chunk_response.status_code == 200

    index_response = client.post(
        "/api/v1/retrieval/index",
        json={
            "team_id": team_id,
            "document_ids": [alpha_id, beta_id],
        },
    )
    assert index_response.status_code == 200

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "question": "哪个文档提到 alerts first?",
            "selected_document_ids": [alpha_id],
            "top_k": 3,
        },
    )

    assert ask_response.status_code == 200
    body = ask_response.json()
    assert body["mode"] == "rag"
    assert body["sources"]
    assert body["sources"][0]["document_id"] == alpha_id
    assert body["sources"][0]["source_name"] == "alpha.md"
    assert body["sources"][0]["snippet"]
    assert all(hit["document_id"] == alpha_id for hit in body["hits"])


def test_chat_ask_supports_none_model_for_forced_mock(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_ask_none_{suffix}"
    user_id = f"u_ask_none_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "NoneModel Team",
            "description": "ask with none model",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Operator",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "question": "hello",
            "model": "none",
            "top_k": 3,
        },
    )

    assert ask_response.status_code == 200
    body = ask_response.json()
    assert body["answer"].startswith("[Mock Chat]")
    assert body["hits"] == []
    assert body["mode"] == "chat"
    assert body["sources"] == []


def test_chat_ask_prefers_multimodal_image_input_when_image_is_selected(client, monkeypatch) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_ask_image_{suffix}"
    user_id = f"u_ask_image_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Image Ask Team",
            "description": "for multimodal image ask",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Vision Operator",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    create_conversation = client.post(
        "/api/v1/conversations",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "title": "Vision Session",
        },
    )
    assert create_conversation.status_code == 201
    conversation_id = create_conversation.json()["conversation_id"]

    upsert_model = client.post(
        "/api/v1/llm/models",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "model_name": "gpt-4.1-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
        },
    )
    assert upsert_model.status_code == 200

    upload_response = client.post(
        "/api/v1/documents/upload",
        data={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "auto_index": "true",
        },
        files={
            "file": ("receipt.png", _build_png_bytes(), "image/png"),
        },
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["document_id"]
    _wait_document_ready(
        client,
        team_id=team_id,
        conversation_id=conversation_id,
        document_id=document_id,
    )

    captured_payload: dict[str, object] = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": "vision-answer",
                        }
                    }
                ]
            }

    def _fake_post(url, headers, json, timeout):  # noqa: ANN001
        captured_payload["url"] = url
        captured_payload["headers"] = headers
        captured_payload["json"] = json
        captured_payload["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr("app.services.llm_service.httpx.post", _fake_post)

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "conversation_id": conversation_id,
            "question": "请直接看图告诉我这是什么内容",
            "selected_document_ids": [document_id],
            "top_k": 3,
            "model": "gpt-4.1-mini",
        },
    )
    assert ask_response.status_code == 200
    assert ask_response.json()["answer"] == "vision-answer"

    user_message = captured_payload["json"]["messages"][1]  # type: ignore[index]
    assert isinstance(user_message["content"], list)
    assert user_message["content"][0]["type"] == "text"
    assert user_message["content"][1]["type"] == "image_url"
    assert str(user_message["content"][1]["image_url"]["url"]).startswith("data:image/png;base64,")


def test_chat_ask_falls_back_when_provider_rejects_multimodal_array_content(client, monkeypatch) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_ask_image_retry_{suffix}"
    user_id = f"u_ask_image_retry_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Image Retry Team",
            "description": "for multimodal retry fallback",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Retry Operator",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    create_conversation = client.post(
        "/api/v1/conversations",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "title": "Retry Session",
        },
    )
    assert create_conversation.status_code == 201
    conversation_id = create_conversation.json()["conversation_id"]

    upsert_model = client.post(
        "/api/v1/llm/models",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "model_name": "gpt-4.1-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
        },
    )
    assert upsert_model.status_code == 200

    upload_response = client.post(
        "/api/v1/documents/upload",
        data={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "auto_index": "true",
        },
        files={
            "file": ("receipt.png", _build_png_bytes(), "image/png"),
        },
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["document_id"]
    _wait_document_ready(
        client,
        team_id=team_id,
        conversation_id=conversation_id,
        document_id=document_id,
    )

    captured_payloads: list[dict[str, object]] = []
    call_count = {"count": 0}

    class _FakeResponse:
        def __init__(self, body: dict[str, object], status_code: int = 200) -> None:
            self._body = body
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
                response = httpx.Response(self.status_code, request=request, json=self._body)
                raise httpx.HTTPStatusError("request failed", request=request, response=response)

        def json(self) -> dict[str, object]:
            return self._body

    def _fake_post(url, headers, json, timeout):  # noqa: ANN001
        captured_payloads.append(json)
        call_count["count"] += 1
        if call_count["count"] == 1:
            return _FakeResponse(
                {
                    "error": {
                        "message": "Invalid type for 'messages[1].content': expected a string, but got an array instead."
                    }
                },
                status_code=400,
            )
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "fallback-after-array-error",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.services.llm_service.httpx.post", _fake_post)

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "conversation_id": conversation_id,
            "question": "Read the attached image.",
            "selected_document_ids": [document_id],
            "top_k": 3,
            "model": "gpt-4.1-mini",
        },
    )
    assert ask_response.status_code == 200
    assert ask_response.json()["answer"] == "fallback-after-array-error"
    assert len(captured_payloads) == 2
    assert isinstance(captured_payloads[0]["messages"][1]["content"], list)  # type: ignore[index]
    second_user_content = captured_payloads[1]["messages"][1]["content"]  # type: ignore[index]
    assert isinstance(second_user_content, str)
    assert "Question:" in second_user_content
    assert "Context:" in second_user_content
    assert "Image attachment: receipt.png" in second_user_content


def test_chat_ask_returns_image_content_parts_and_history_payload(client, monkeypatch) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_output_image_{suffix}"
    user_id = f"u_output_image_{suffix}"
    image_bytes = b"\x89PNG\r\n\x1a\nPNGDATA"
    expected_data_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Output Image Team",
            "description": "for model image output",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Image Operator",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    upsert_model = client.post(
        "/api/v1/llm/models",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "model_name": "gpt-4.1-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
        },
    )
    assert upsert_model.status_code == 200

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "Here is the generated diagram."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": "https://cdn.example.com/generated/diagram.png?signature=test",
                                    },
                                },
                            ],
                        },
                        "finish_reason": "stop",
                    }
                ]
            }

    def _fake_post(url, headers, json, timeout):  # noqa: ANN001, ARG001
        return _FakeResponse()

    def _fake_get(url, follow_redirects, timeout):  # noqa: ANN001, ARG001
        assert url == "https://cdn.example.com/generated/diagram.png?signature=test"
        assert follow_redirects is True
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "image/png"},
            content=image_bytes,
        )

    monkeypatch.setattr("app.services.llm_service.httpx.post", _fake_post)
    monkeypatch.setattr("app.services.llm_service.httpx.get", _fake_get)

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "question": "Generate a diagram image.",
            "top_k": 3,
            "model": "gpt-4.1-mini",
        },
    )
    assert ask_response.status_code == 200
    body = ask_response.json()
    assert body["answer"] == "Here is the generated diagram."
    assert body["content_parts"] == [
        {
            "type": "text",
            "text": "Here is the generated diagram.",
            "url": None,
            "original_url": None,
            "mime_type": None,
            "alt": None,
        },
        {
            "type": "image",
            "text": None,
            "url": expected_data_url,
            "original_url": "https://cdn.example.com/generated/diagram.png?signature=test",
            "mime_type": "image/png",
            "alt": None,
        },
    ]

    history_response = client.get(
        "/api/v1/chat/history",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "limit": 20,
        },
    )
    assert history_response.status_code == 200
    items = history_response.json()["items"]
    assert len(items) == 1
    assert items[0]["response_text"] == "Here is the generated diagram."
    assert items[0]["response_payload"]["content_parts"] == body["content_parts"]


def test_chat_ask_extracts_markdown_image_text_into_content_parts(client, monkeypatch) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_markdown_image_{suffix}"
    user_id = f"u_markdown_image_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Markdown Image Team",
            "description": "for markdown image output",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Markdown Operator",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    upsert_model = client.post(
        "/api/v1/llm/models",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "model_name": "gpt-4.1-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
        },
    )
    assert upsert_model.status_code == 200

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": "![Generated Image](data:image/jpeg;base64,/9j/AAAA)",
                        },
                        "finish_reason": "stop",
                    }
                ]
            }

    def _fake_post(url, headers, json, timeout):  # noqa: ANN001, ARG001
        return _FakeResponse()

    monkeypatch.setattr("app.services.llm_service.httpx.post", _fake_post)

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "question": "Generate a diagram image.",
            "top_k": 3,
            "model": "gpt-4.1-mini",
        },
    )
    assert ask_response.status_code == 200
    body = ask_response.json()
    assert body["answer"] == "Image output"
    assert body["content_parts"] == [
        {
            "type": "image",
            "text": None,
            "url": "data:image/jpeg;base64,/9j/AAAA",
            "original_url": None,
            "mime_type": "image/jpeg",
            "alt": "Generated Image",
        }
    ]


def test_chat_action_create_incident(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_action_{suffix}"
    user_id = f"u_action_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Action Team",
            "description": "for action tool",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Runner",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    response = client.post(
        "/api/v1/chat/action",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "action": "create_incident",
            "arguments": {
                "title": "Database CPU usage above threshold",
                "severity": "P1",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "create_incident"
    assert body["result"]["tool_name"] == "create_incident"
    assert body["result"]["incident"]["title"] == "Database CPU usage above threshold"
    assert body["result"]["incident"]["severity"] == "P1"
    assert body["result"]["incident"]["status"] == "open"


def test_chat_action_list_recent_documents(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_action_docs_{suffix}"
    user_id = f"u_action_docs_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Action Docs Team",
            "description": "for list docs tool",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Runner",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    first_doc = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "ops-a.md",
            "content_type": "md",
            "content": "A",
        },
    )
    assert first_doc.status_code == 201

    second_doc = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "ops-b.md",
            "content_type": "md",
            "content": "B",
        },
    )
    assert second_doc.status_code == 201

    response = client.post(
        "/api/v1/chat/action",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "action": "list_recent_documents",
            "arguments": {"limit": 2},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["tool_name"] == "list_recent_documents"
    assert len(body["result"]["documents"]) == 2
    assert body["result"]["documents"][0]["source_name"] == "ops-b.md"
    assert body["result"]["documents"][1]["source_name"] == "ops-a.md"


def test_chat_action_rejects_unknown_action(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_action_unknown_{suffix}"
    user_id = f"u_action_unknown_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Action Unknown Team",
            "description": "for unknown action",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Runner",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    response = client.post(
        "/api/v1/chat/action",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "action": "shutdown_cluster",
            "arguments": {},
        },
    )

    assert response.status_code == 400

def test_chat_action_rejects_invalid_incident_payload(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_action_invalid_{suffix}"
    user_id = f"u_action_invalid_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Action Invalid Team",
            "description": "for invalid payload",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Runner",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    response = client.post(
        "/api/v1/chat/action",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "action": "create_incident",
            "arguments": {},
        },
    )

    assert response.status_code == 400


def test_chat_ask_rejects_unconfigured_custom_model(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_ask_model_{suffix}"
    user_id = f"u_ask_model_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "AskModel Team",
            "description": "for ask model config",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Operator",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "question": "hello",
            "model": "gpt-4.1-mini",
        },
    )
    assert ask_response.status_code == 404


def test_chat_history_delete_message(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id, conversation_id = _create_team_user_and_conversation(client, suffix)

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "conversation_id": conversation_id,
            "question": "first message",
        },
    )
    assert ask_response.status_code == 200

    history_before = client.get(
        "/api/v1/chat/history",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "limit": 20,
        },
    )
    assert history_before.status_code == 200
    assert len(history_before.json()["items"]) == 1
    message_id = history_before.json()["items"][0]["message_id"]

    delete_response = client.delete(
        f"/api/v1/chat/history/{message_id}",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
        },
    )
    assert delete_response.status_code == 204

    history_after = client.get(
        "/api/v1/chat/history",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "limit": 20,
        },
    )
    assert history_after.status_code == 200
    assert history_after.json()["items"] == []


def test_chat_history_edit_user_message(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id, conversation_id = _create_team_user_and_conversation(client, suffix)

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "conversation_id": conversation_id,
            "question": "old text",
        },
    )
    assert ask_response.status_code == 200

    history_before = client.get(
        "/api/v1/chat/history",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "limit": 20,
        },
    )
    assert history_before.status_code == 200
    assert len(history_before.json()["items"]) == 1
    item_before = history_before.json()["items"][0]
    message_id = item_before["message_id"]

    edit_response = client.put(
        f"/api/v1/chat/history/{message_id}",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "request_text": "new text",
        },
    )
    assert edit_response.status_code == 200
    edited = edit_response.json()
    assert edited["request_text"] == "new text"
    assert edited["response_text"].startswith("[Mock Chat]")

    history_after = client.get(
        "/api/v1/chat/history",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "limit": 20,
        },
    )
    assert history_after.status_code == 200
    assert len(history_after.json()["items"]) == 1
    item_after = history_after.json()["items"][0]
    assert item_after["message_id"] == message_id
    assert item_after["request_text"] == "new text"
