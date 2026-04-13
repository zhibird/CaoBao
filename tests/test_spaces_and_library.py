import json
from uuid import uuid4

from tests.auth_helpers import register_workspace_user, register_workspace_user_in_team


def _create_team_and_user(client, suffix: str) -> tuple[str, str]:
    return register_workspace_user(
        client,
        prefix=f"space_{suffix}",
        display_name="Space User",
    )


def _create_space(
    client,
    *,
    team_id: str,
    user_id: str,
    name: str,
    description: str | None = None,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/spaces",
        json={
            "team_id": "ignored-team",
            "user_id": "ignored-user",
            "name": name,
            "description": description,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["team_id"] == team_id
    assert body["owner_user_id"] == user_id
    return body


def _create_conversation(client, *, team_id: str, user_id: str, title: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/conversations",
        json={
            "team_id": "ignored-team",
            "user_id": "ignored-user",
            "title": title,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["team_id"] == team_id
    assert body["user_id"] == user_id
    return body


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
            "team_id": "ignored-team",
            "user_id": "ignored-user",
            "conversation_id": conversation_id,
            "message": "Publish this answer into the library.",
        },
    )
    assert echo_response.status_code == 200
    body = echo_response.json()
    assert body["team_id"] == team_id
    assert body["user_id"] == user_id

    history_response = client.get(
        "/api/v1/chat/history",
        params={
            "conversation_id": conversation_id,
            "limit": 1,
        },
    )
    assert history_response.status_code == 200
    items = history_response.json()["items"]
    assert len(items) == 1
    return items[0]["message_id"]


def test_space_and_library_routes_require_authenticated_user(client) -> None:
    client.cookies.clear()

    spaces_response = client.get("/api/v1/spaces", params={"limit": 20})
    assert spaces_response.status_code == 401

    library_list_response = client.get(
        "/api/v1/library/documents",
        params={"space_id": str(uuid4())},
    )
    assert library_list_response.status_code == 401

    library_publish_response = client.post(
        "/api/v1/library/documents/publish-from-conversation",
        json={"document_id": str(uuid4())},
    )
    assert library_publish_response.status_code == 401


def test_space_routes_ignore_client_identity_and_list_user_spaces(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)

    created_space = _create_space(
        client,
        team_id=team_id,
        user_id=user_id,
        name="Research Vault",
        description="for durable notes",
    )

    list_response = client.get(
        "/api/v1/spaces",
        params={"limit": 20},
    )
    assert list_response.status_code == 200
    spaces = list_response.json()
    assert any(space["space_id"] == created_space["space_id"] for space in spaces)
    assert any(space["is_default"] is True for space in spaces)


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
        params={"limit": 20},
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
            "team_id": "ignored-team",
            "user_id": "ignored-user",
            "document_id": document_id,
            "conversation_id": conversation_id,
        },
    )
    assert publish_response.status_code == 201
    published = publish_response.json()
    assert published["team_id"] == team_id
    assert published["conversation_id"] is None
    assert published["space_id"] == space_id
    assert published["visibility"] == "space"
    assert published["asset_kind"] == "knowledge_doc"
    assert published["origin_document_id"] == document_id

    library_response = client.get(
        "/api/v1/library/documents",
        params={"space_id": space_id},
    )
    assert library_response.status_code == 200
    documents = library_response.json()
    assert len(documents) == 1
    assert documents[0]["document_id"] == published["document_id"]


def test_publish_from_conversation_requires_space_ownership_when_space_is_omitted(client) -> None:
    owner_team_id, owner_user_id = _create_team_and_user(client, uuid4().hex[:8])
    conversation = _create_conversation(
        client,
        team_id=owner_team_id,
        user_id=owner_user_id,
        title="Owner Publish Session",
    )
    document_id = _import_and_index_document(
        client,
        team_id=owner_team_id,
        conversation_id=conversation["conversation_id"],
        source_name="publish.md",
        content="# Publish\n\nThis should stay with the owner.",
    )

    peer_team_id, peer_user_id = register_workspace_user_in_team(
        client,
        team_id=owner_team_id,
        prefix="space_peer",
        display_name="Space Peer",
    )
    assert peer_team_id == owner_team_id
    assert peer_user_id != owner_user_id

    publish_response = client.post(
        "/api/v1/library/documents/publish-from-conversation",
        json={
            "document_id": document_id,
            "conversation_id": conversation["conversation_id"],
        },
    )
    assert publish_response.status_code == 404


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
        params={"space_id": conversation["space_id"]},
    )
    assert library_response.status_code == 200
    documents = library_response.json()
    assert len(documents) == 1
    listed_meta = json.loads(documents[0]["meta_json"])
    assert listed_meta["source_message_id"] == message_id


def test_space_and_library_routes_hide_foreign_resources(client) -> None:
    owner_team_id, owner_user_id = register_workspace_user(
        client,
        prefix="space_owner",
        display_name="Owner",
    )
    owned_space = _create_space(
        client,
        team_id=owner_team_id,
        user_id=owner_user_id,
        name="Owner Space",
    )
    conversation = _create_conversation(
        client,
        team_id=owner_team_id,
        user_id=owner_user_id,
        title="Owner Session",
    )
    document_id = _import_and_index_document(
        client,
        team_id=owner_team_id,
        conversation_id=conversation["conversation_id"],
        source_name="owner.md",
        content="# Owner\n\nOnly the owner should be able to publish this.",
    )

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    intruder_team_id, intruder_user_id = register_workspace_user(
        client,
        prefix="space_intruder",
        display_name="Intruder",
    )
    assert intruder_team_id != owner_team_id
    assert intruder_user_id != owner_user_id

    patch_response = client.patch(
        f"/api/v1/spaces/{owned_space['space_id']}",
        json={
            "team_id": "ignored-team",
            "user_id": "ignored-user",
            "name": "stolen",
        },
    )
    assert patch_response.status_code == 404
    assert patch_response.json()["detail"] == f"Space '{owned_space['space_id']}' not found."

    delete_response = client.delete(f"/api/v1/spaces/{owned_space['space_id']}")
    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == f"Space '{owned_space['space_id']}' not found."

    list_response = client.get(
        "/api/v1/library/documents",
        params={"space_id": owned_space["space_id"]},
    )
    assert list_response.status_code == 404
    assert list_response.json()["detail"] == f"Space '{owned_space['space_id']}' not found."

    publish_foreign_response = client.post(
        "/api/v1/library/documents/publish-from-conversation",
        json={
            "document_id": document_id,
            "conversation_id": conversation["conversation_id"],
        },
    )
    assert publish_foreign_response.status_code == 404
    assert publish_foreign_response.json()["detail"] == f"Document '{document_id}' not found."
