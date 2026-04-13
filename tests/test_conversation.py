from uuid import uuid4

from tests.auth_helpers import register_workspace_user


def _create_team_and_user(client, suffix: str) -> tuple[str, str]:
    return register_workspace_user(client, prefix=f"conv_{suffix}", display_name="Conversation User")


def _create_conversation(client, team_id: str, user_id: str, title: str) -> str:
    response = client.post(
        "/api/v1/conversations",
        json={"title": title},
    )
    assert response.status_code == 201
    assert response.json()["team_id"] == team_id
    assert response.json()["user_id"] == user_id
    return response.json()["conversation_id"]


def test_conversations_require_authenticated_user(client) -> None:
    client.cookies.clear()
    response = client.get("/api/v1/conversations", params={"limit": 20})
    assert response.status_code == 401


def test_create_list_delete_conversation(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)

    conversation_id = _create_conversation(
        client=client,
        team_id=team_id,
        user_id=user_id,
        title="Session One",
    )

    list_response = client.get(
        "/api/v1/conversations",
        params={"limit": 20},
    )
    assert list_response.status_code == 200
    listed_ids = [item["conversation_id"] for item in list_response.json()]
    assert conversation_id in listed_ids

    delete_response = client.delete(
        f"/api/v1/conversations/{conversation_id}",
    )
    assert delete_response.status_code == 204

    list_after_delete = client.get(
        "/api/v1/conversations",
        params={"limit": 20},
    )
    assert list_after_delete.status_code == 200
    listed_ids_after = [item["conversation_id"] for item in list_after_delete.json()]
    assert conversation_id not in listed_ids_after


def test_rename_conversation(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)

    conversation_id = _create_conversation(
        client=client,
        team_id=team_id,
        user_id=user_id,
        title="Before Rename",
    )

    rename_response = client.patch(
        f"/api/v1/conversations/{conversation_id}",
        json={"title": "After Rename"},
    )
    assert rename_response.status_code == 200
    assert rename_response.json()["title"] == "After Rename"

    list_response = client.get(
        "/api/v1/conversations",
        params={"limit": 20},
    )
    assert list_response.status_code == 200
    listed = {item["conversation_id"]: item for item in list_response.json()}
    assert listed[conversation_id]["title"] == "After Rename"


def test_pin_conversation_and_list_priority(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)

    first_id = _create_conversation(client, team_id, user_id, "First")
    second_id = _create_conversation(client, team_id, user_id, "Second")

    pin_response = client.patch(
        f"/api/v1/conversations/{first_id}/pin",
        json={"pinned": True},
    )
    assert pin_response.status_code == 200
    assert pin_response.json()["is_pinned"] is True

    listed = client.get(
        "/api/v1/conversations",
        params={"limit": 20},
    )
    assert listed.status_code == 200
    items = listed.json()
    assert items[0]["conversation_id"] == first_id
    assert items[0]["is_pinned"] is True
    assert any(item["conversation_id"] == second_id for item in items)


def test_conversation_scoped_documents_and_history(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)

    conversation_a = _create_conversation(client, team_id, user_id, "Session A")
    conversation_b = _create_conversation(client, team_id, user_id, "Session B")

    import_response = client.post(
        "/api/v1/documents/import",
        json={
            "team_id": team_id,
            "conversation_id": conversation_a,
            "source_name": "session-a.md",
            "content_type": "md",
            "content": "# A\n\nOnly for conversation A",
        },
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["document_id"]

    list_a = client.get(
        "/api/v1/documents",
        params={"team_id": team_id, "conversation_id": conversation_a},
    )
    assert list_a.status_code == 200
    ids_a = [item["document_id"] for item in list_a.json()]
    assert document_id in ids_a

    list_b = client.get(
        "/api/v1/documents",
        params={"team_id": team_id, "conversation_id": conversation_b},
    )
    assert list_b.status_code == 200
    ids_b = [item["document_id"] for item in list_b.json()]
    assert document_id not in ids_b

    ask_a = client.post(
        "/api/v1/chat/ask",
        json={
            "conversation_id": conversation_a,
            "question": "hello from A",
        },
    )
    assert ask_a.status_code == 200

    ask_b = client.post(
        "/api/v1/chat/ask",
        json={
            "conversation_id": conversation_b,
            "question": "hello from B",
        },
    )
    assert ask_b.status_code == 200

    history_a = client.get(
        "/api/v1/chat/history",
        params={"conversation_id": conversation_a, "limit": 20},
    )
    assert history_a.status_code == 200
    assert history_a.json()["conversation_id"] == conversation_a
    assert all(item["conversation_id"] == conversation_a for item in history_a.json()["items"])

    history_b = client.get(
        "/api/v1/chat/history",
        params={"conversation_id": conversation_b, "limit": 20},
    )
    assert history_b.status_code == 200
    assert history_b.json()["conversation_id"] == conversation_b
    assert all(item["conversation_id"] == conversation_b for item in history_b.json()["items"])

    delete_a = client.delete(
        f"/api/v1/conversations/{conversation_a}",
    )
    assert delete_a.status_code == 204

    docs_after_delete = client.get(
        "/api/v1/documents",
        params={"team_id": team_id, "conversation_id": conversation_a},
    )
    assert docs_after_delete.status_code == 404


def test_conversation_routes_hide_foreign_resources(client) -> None:
    owner_team_id, owner_user_id = register_workspace_user(
        client,
        prefix="conv_owner",
        display_name="Owner",
    )
    create_response = client.post(
        "/api/v1/conversations",
        json={"title": "Owner Conversation"},
    )
    assert create_response.status_code == 201
    conversation = create_response.json()
    assert conversation["team_id"] == owner_team_id
    assert conversation["user_id"] == owner_user_id

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    intruder_team_id, intruder_user_id = register_workspace_user(
        client,
        prefix="conv_intruder",
        display_name="Intruder",
    )
    assert intruder_team_id != owner_team_id
    assert intruder_user_id != owner_user_id

    list_response = client.get(
        "/api/v1/conversations",
        params={"space_id": conversation["space_id"], "limit": 20},
    )
    assert list_response.status_code == 404
    assert list_response.json()["detail"] == f"Space '{conversation['space_id']}' not found."

    delete_response = client.delete(f"/api/v1/conversations/{conversation['conversation_id']}")
    assert delete_response.status_code == 404
    assert (
        delete_response.json()["detail"]
        == f"Conversation '{conversation['conversation_id']}' not found."
    )
