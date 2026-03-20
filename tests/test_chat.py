from uuid import uuid4


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
