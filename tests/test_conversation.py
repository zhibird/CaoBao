from uuid import uuid4


def _create_team_and_user(client, suffix: str) -> tuple[str, str]:
    team_id = f"team_conv_{suffix}"
    user_id = f"u_conv_{suffix}"

    create_team = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Conversation Team",
            "description": "for conversation tests",
        },
    )
    assert create_team.status_code == 201

    create_user = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Conversation User",
            "role": "member",
        },
    )
    assert create_user.status_code == 201

    return team_id, user_id


def _create_conversation(client, team_id: str, user_id: str, title: str) -> str:
    response = client.post(
        "/api/v1/conversations",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "title": title,
        },
    )
    assert response.status_code == 201
    return response.json()["conversation_id"]


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
        params={
            "team_id": team_id,
            "user_id": user_id,
            "limit": 20,
        },
    )
    assert list_response.status_code == 200
    listed_ids = [item["conversation_id"] for item in list_response.json()]
    assert conversation_id in listed_ids

    delete_response = client.delete(
        f"/api/v1/conversations/{conversation_id}",
        params={
            "team_id": team_id,
            "user_id": user_id,
        },
    )
    assert delete_response.status_code == 204

    list_after_delete = client.get(
        "/api/v1/conversations",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "limit": 20,
        },
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
        json={
            "team_id": team_id,
            "user_id": user_id,
            "title": "After Rename",
        },
    )
    assert rename_response.status_code == 200
    assert rename_response.json()["title"] == "After Rename"

    list_response = client.get(
        "/api/v1/conversations",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "limit": 20,
        },
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
        json={
            "team_id": team_id,
            "user_id": user_id,
            "pinned": True,
        },
    )
    assert pin_response.status_code == 200
    assert pin_response.json()["is_pinned"] is True

    listed = client.get(
        "/api/v1/conversations",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "limit": 20,
        },
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
            "user_id": user_id,
            "team_id": team_id,
            "conversation_id": conversation_a,
            "question": "hello from A",
        },
    )
    assert ask_a.status_code == 200

    ask_b = client.post(
        "/api/v1/chat/ask",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "conversation_id": conversation_b,
            "question": "hello from B",
        },
    )
    assert ask_b.status_code == 200

    history_a = client.get(
        "/api/v1/chat/history",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_a,
            "limit": 20,
        },
    )
    assert history_a.status_code == 200
    assert history_a.json()["conversation_id"] == conversation_a
    assert all(item["conversation_id"] == conversation_a for item in history_a.json()["items"])

    history_b = client.get(
        "/api/v1/chat/history",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "conversation_id": conversation_b,
            "limit": 20,
        },
    )
    assert history_b.status_code == 200
    assert history_b.json()["conversation_id"] == conversation_b
    assert all(item["conversation_id"] == conversation_b for item in history_b.json()["items"])

    delete_a = client.delete(
        f"/api/v1/conversations/{conversation_a}",
        params={"team_id": team_id, "user_id": user_id},
    )
    assert delete_a.status_code == 204

    docs_after_delete = client.get(
        "/api/v1/documents",
        params={"team_id": team_id, "conversation_id": conversation_a},
    )
    assert docs_after_delete.status_code == 200
    assert docs_after_delete.json() == []
