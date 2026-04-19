from uuid import uuid4

from tests.auth_helpers import register_workspace_user


def test_chat_history_records_echo(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = register_workspace_user(
        client,
        prefix=f"history_echo_{suffix}",
        display_name="Echo User",
    )

    chat_response = client.post(
        "/api/v1/chat/echo",
        json={
            "message": "hello history",
        },
    )
    assert chat_response.status_code == 200

    history_response = client.get(
        "/api/v1/chat/history",
        params={
            "limit": 5,
        },
    )
    assert history_response.status_code == 200

    body = history_response.json()
    assert body["team_id"] == team_id
    assert body["user_id"] == user_id
    assert len(body["items"]) >= 1

    latest = body["items"][0]
    assert latest["channel"] == "echo"
    assert latest["request_text"] == "hello history"
    assert latest["response_text"] == "[Echo] hello history"
    assert latest["request_payload"]["message"] == "hello history"


def test_chat_history_records_ask_and_action(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = register_workspace_user(
        client,
        prefix=f"history_flow_{suffix}",
        display_name="Flow User",
    )

    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "source_name": "ops.md",
            "content_type": "md",
            "content": "# Ops Guide\n\nAlways check alerts first.",
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
            "question": "alerts first?",
            "top_k": 3,
            "document_id": document_id,
        },
    )
    assert ask_response.status_code == 200

    action_response = client.post(
        "/api/v1/chat/action",
        json={
            "action": "create_incident",
            "arguments": {
                "title": "Service timeout spike",
                "severity": "P2",
            },
        },
    )
    assert action_response.status_code == 200

    history_response = client.get(
        "/api/v1/chat/history",
        params={
            "limit": 10,
        },
    )
    assert history_response.status_code == 200
    items = history_response.json()["items"]
    channels = [item["channel"] for item in items]

    assert "ask" in channels
    assert "action" in channels
    assert channels.index("action") < channels.index("ask")

    ask_item = next(item for item in items if item["channel"] == "ask")
    action_item = next(item for item in items if item["channel"] == "action")

    assert ask_item["request_text"] == "alerts first?"
    assert action_item["request_text"] == "create_incident"
    assert "Incident created successfully." in action_item["response_text"]


def test_chat_history_requires_authenticated_user(client) -> None:
    client.cookies.clear()

    response = client.get("/api/v1/chat/history", params={"limit": 5})

    assert response.status_code == 401
