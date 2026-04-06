from uuid import uuid4


def _create_team_and_user(client, suffix: str) -> tuple[str, str]:
    team_id = f"team_memory_{suffix}"
    user_id = f"user_memory_{suffix}"

    team_response = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Memory Team",
            "description": "for memory tests",
        },
    )
    assert team_response.status_code == 201

    user_response = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Memory User",
            "role": "member",
        },
    )
    assert user_response.status_code == 201
    return team_id, user_id


def _create_space(client, *, team_id: str, user_id: str, name: str) -> str:
    response = client.post(
        "/api/v1/spaces",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "name": name,
            "description": "space for memory isolation",
        },
    )
    assert response.status_code == 201
    return response.json()["space_id"]


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
            "message": "Remember this answer.",
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


def test_memory_cards_crud_happy_path(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    space_id = _create_space(client, team_id=team_id, user_id=user_id, name="Memory Space")

    create_response = client.post(
        "/api/v1/memory/cards",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
            "title": "Project codename",
            "content": "The internal codename is Atlas.",
            "category": "fact",
            "weight": 0.9,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["team_id"] == team_id
    assert created["user_id"] == user_id
    assert created["space_id"] == space_id
    assert created["status"] == "active"
    assert created["title"] == "Project codename"
    memory_id = created["memory_id"]

    list_response = client.get(
        "/api/v1/memory/cards",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
            "limit": 50,
        },
    )
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["memory_id"] == memory_id

    update_response = client.patch(
        f"/api/v1/memory/cards/{memory_id}",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "title": "Project codename updated",
            "content": "The codename changed to Orion.",
            "status": "disabled",
            "weight": 0.7,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["title"] == "Project codename updated"
    assert updated["content"] == "The codename changed to Orion."
    assert updated["status"] == "disabled"
    assert updated["weight"] == 0.7

    delete_response = client.delete(
        f"/api/v1/memory/cards/{memory_id}",
        params={
            "team_id": team_id,
            "user_id": user_id,
        },
    )
    assert delete_response.status_code == 204

    list_after_delete = client.get(
        "/api/v1/memory/cards",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
            "limit": 50,
        },
    )
    assert list_after_delete.status_code == 200
    assert list_after_delete.json() == []


def test_memory_cards_validation_rejects_invalid_status(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    space_id = _create_space(client, team_id=team_id, user_id=user_id, name="Validation Space")

    create_response = client.post(
        "/api/v1/memory/cards",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
            "title": "Bad status card",
            "content": "invalid status case",
            "status": "deleted",
        },
    )
    assert create_response.status_code == 422


def test_memory_cards_are_isolated_by_space(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    space_a = _create_space(client, team_id=team_id, user_id=user_id, name="Space A")
    space_b = _create_space(client, team_id=team_id, user_id=user_id, name="Space B")

    create_response = client.post(
        "/api/v1/memory/cards",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_a,
            "title": "Space A memory",
            "content": "Only visible in space A.",
            "category": "constraint",
        },
    )
    assert create_response.status_code == 201

    list_space_a = client.get(
        "/api/v1/memory/cards",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_a,
        },
    )
    assert list_space_a.status_code == 200
    assert len(list_space_a.json()) == 1

    list_space_b = client.get(
        "/api/v1/memory/cards",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_b,
        },
    )
    assert list_space_b.status_code == 200
    assert list_space_b.json() == []


def test_memory_cards_can_track_source_message(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    conversation = _create_conversation(
        client,
        team_id=team_id,
        user_id=user_id,
        title="Memory Source Conversation",
    )
    space_id = conversation["space_id"]
    message_id = _create_history_message(
        client,
        team_id=team_id,
        user_id=user_id,
        conversation_id=conversation["conversation_id"],
    )

    create_response = client.post(
        "/api/v1/memory/cards",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
            "title": "Remembered answer",
            "content": "This answer should remain linked to the original message.",
            "category": "assistant_answer",
            "source_message_id": message_id,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["source_message_id"] == message_id

    list_response = client.get(
        "/api/v1/memory/cards",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
            "limit": 50,
        },
    )
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["source_message_id"] == message_id
