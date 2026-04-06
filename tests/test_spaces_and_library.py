import json
from uuid import uuid4


def _create_team_and_user(client, suffix: str) -> tuple[str, str]:
    team_id = f"team_space_{suffix}"
    user_id = f"user_space_{suffix}"

    team_response = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Space Team",
            "description": "for space tests",
        },
    )
    assert team_response.status_code == 201

    user_response = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Space User",
            "role": "member",
        },
    )
    assert user_response.status_code == 201
    return team_id, user_id


def _create_conversation(client, *, team_id: str, user_id: str, title: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/conversations",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "title": title,
        },
    )
    assert response.status_code == 201
    return response.json()


def _import_and_index_document(
    client,
    *,
    team_id: str,
    conversation_id: str,
    source_name: str,
    content: str,
) -> str:
    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "conversation_id": conversation_id,
            "source_name": source_name,
            "content_type": "md",
            "content": content,
        },
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["document_id"]

    chunk_response = client.post(
        f"/api/v1/documents/{document_id}/chunk",
        json={
            "team_id": team_id,
            "conversation_id": conversation_id,
            "max_chars": 120,
            "overlap": 10,
        },
    )
    assert chunk_response.status_code == 200

    index_response = client.post(
        "/api/v1/retrieval/index",
        json={
            "team_id": team_id,
            "conversation_id": conversation_id,
            "document_id": document_id,
        },
    )
    assert index_response.status_code == 200
    return document_id


def _create_history_message(
    client,
    *,
    team_id: str,
    user_id: str,
    conversation_id: str,
) -> str:
    echo_response = client.post(
        "/api/v1/chat/echo",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "message": "Publish this answer into the library.",
        },
    )
    assert echo_response.status_code == 200

    history_response = client.get(
        "/api/v1/chat/history",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "limit": 1,
        },
    )
    assert history_response.status_code == 200
    items = history_response.json()["items"]
    assert len(items) == 1
    return items[0]["message_id"]


def test_conversation_creation_auto_provisions_default_space(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)

    conversation = _create_conversation(
        client,
        team_id=team_id,
        user_id=user_id,
        title="Project Session",
    )
    assert conversation["space_id"]

    spaces_response = client.get(
        "/api/v1/spaces",
        params={
            "team_id": team_id,
            "user_id": user_id,
        },
    )
    assert spaces_response.status_code == 200
    spaces = spaces_response.json()
    assert len(spaces) == 1
    assert spaces[0]["space_id"] == conversation["space_id"]
    assert spaces[0]["is_default"] is True


def test_publish_conversation_document_to_library(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    conversation = _create_conversation(
        client,
        team_id=team_id,
        user_id=user_id,
        title="Research Session",
    )
    conversation_id = conversation["conversation_id"]
    space_id = conversation["space_id"]

    document_id = _import_and_index_document(
        client,
        team_id=team_id,
        conversation_id=conversation_id,
        source_name="runbook.md",
        content="# Runbook\n\nAlways inspect the payment retry queue first.",
    )

    publish_response = client.post(
        "/api/v1/library/documents/publish-from-conversation",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "document_id": document_id,
            "conversation_id": conversation_id,
        },
    )
    assert publish_response.status_code == 201
    published = publish_response.json()
    assert published["conversation_id"] is None
    assert published["space_id"] == space_id
    assert published["visibility"] == "space"
    assert published["asset_kind"] == "knowledge_doc"
    assert published["origin_document_id"] == document_id

    library_response = client.get(
        "/api/v1/library/documents",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
        },
    )
    assert library_response.status_code == 200
    documents = library_response.json()
    assert len(documents) == 1
    assert documents[0]["document_id"] == published["document_id"]


def test_chat_ask_uses_library_documents_across_conversations_in_same_space(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    source_conversation = _create_conversation(
        client,
        team_id=team_id,
        user_id=user_id,
        title="Source Session",
    )
    target_conversation = _create_conversation(
        client,
        team_id=team_id,
        user_id=user_id,
        title="Target Session",
    )
    assert source_conversation["space_id"] == target_conversation["space_id"]

    document_id = _import_and_index_document(
        client,
        team_id=team_id,
        conversation_id=source_conversation["conversation_id"],
        source_name="ops.md",
        content="# Ops\n\nThe deployment codename for the mobile release is Atlas.",
    )

    publish_response = client.post(
        "/api/v1/library/documents/publish-from-conversation",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "document_id": document_id,
            "conversation_id": source_conversation["conversation_id"],
        },
    )
    assert publish_response.status_code == 201
    published_document_id = publish_response.json()["document_id"]

    ask_response = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "conversation_id": target_conversation["conversation_id"],
            "question": "What is the deployment codename for the mobile release?",
            "top_k": 3,
        },
    )
    assert ask_response.status_code == 200
    body = ask_response.json()
    assert body["mode"] == "rag"
    assert body["space_id"] == target_conversation["space_id"]
    assert any(hit["document_id"] == published_document_id for hit in body["hits"])
    assert any(source["document_id"] == published_document_id for source in body["sources"])


def test_library_import_can_persist_source_message_metadata(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    conversation = _create_conversation(
        client,
        team_id=team_id,
        user_id=user_id,
        title="Capture Conversation",
    )
    message_id = _create_history_message(
        client,
        team_id=team_id,
        user_id=user_id,
        conversation_id=conversation["conversation_id"],
    )

    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": conversation["space_id"],
            "source_name": f"answer-{message_id}.md",
            "content_type": "md",
            "content": "# Captured Answer\n\nKeep this answer reusable.",
            "auto_index": True,
            "meta": {
                "source_message_id": message_id,
                "capture_kind": "assistant_answer",
            },
        },
    )
    assert import_response.status_code == 201
    created = import_response.json()
    meta = json.loads(created["meta_json"])
    assert meta["source_message_id"] == message_id
    assert created["space_id"] == conversation["space_id"]
    assert created["visibility"] == "space"

    library_response = client.get(
        "/api/v1/library/documents",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": conversation["space_id"],
        },
    )
    assert library_response.status_code == 200
    documents = library_response.json()
    assert len(documents) == 1
    listed_meta = json.loads(documents[0]["meta_json"])
    assert listed_meta["source_message_id"] == message_id
