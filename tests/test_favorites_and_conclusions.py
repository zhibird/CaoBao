from uuid import uuid4

import pytest


def _create_team_and_user(client, suffix: str) -> tuple[str, str]:
    team_id = f"team_phase3_{suffix}"
    user_id = f"user_phase3_{suffix}"

    team_response = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Phase3 Team",
            "description": "for favorites and conclusions tests",
        },
    )
    assert team_response.status_code == 201

    user_response = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Phase3 User",
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
            "description": "phase3 space",
        },
    )
    assert response.status_code == 201
    return response.json()["space_id"]


def _create_conversation(client, *, team_id: str, user_id: str, title: str) -> str:
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
            "message": "Snapshot this message.",
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


def _create_favorite(
    client,
    *,
    team_id: str,
    user_id: str,
    space_id: str,
    conversation_id: str,
    message_id: str,
) -> dict:
    response = client.post(
        "/api/v1/favorites/answers",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
            "message_id": message_id,
            "title": "Saved Answer",
            "note": "keep this one",
            "tags": ["phase3", "favorite"],
        },
    )
    assert response.status_code == 201
    return response.json()


def _promote(client, *, favorite_id: str, target: str, team_id: str, user_id: str, space_id: str):
    url = f"/api/v1/favorites/answers/{favorite_id}/promote-to-{target}"
    return client.post(
        url,
        json={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
        },
    )


def test_favorites_crud_and_access_boundary(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    other_user_id = f"user_other_{suffix}"
    other_user_response = client.post(
        "/api/v1/users",
        json={
            "user_id": other_user_id,
            "team_id": team_id,
            "display_name": "Other User",
            "role": "member",
        },
    )
    assert other_user_response.status_code == 201

    space_id = _create_space(client, team_id=team_id, user_id=user_id, name="Favorites Space")
    conversation_id = _create_conversation(
        client,
        team_id=team_id,
        user_id=user_id,
        title="Favorites Conversation",
    )
    message_id = _create_history_message(
        client,
        team_id=team_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    favorite = _create_favorite(
        client,
        team_id=team_id,
        user_id=user_id,
        space_id=space_id,
        conversation_id=conversation_id,
        message_id=message_id,
    )
    favorite_id = favorite["favorite_id"]

    list_response = client.get(
        "/api/v1/favorites/answers",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
        },
    )
    assert list_response.status_code == 200
    listed = list_response.json()
    assert any(item["favorite_id"] == favorite_id for item in listed)

    patch_response = client.patch(
        f"/api/v1/favorites/answers/{favorite_id}",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "title": "Saved Answer Updated",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Saved Answer Updated"

    forbidden = client.get(
        "/api/v1/favorites/answers",
        params={
            "team_id": team_id,
            "user_id": other_user_id,
            "space_id": space_id,
        },
    )
    assert forbidden.status_code in {400, 404}

    delete_response = client.delete(
        f"/api/v1/favorites/answers/{favorite_id}",
        params={
            "team_id": team_id,
            "user_id": user_id,
        },
    )
    assert delete_response.status_code == 204


def test_promote_favorite_to_memory_and_conclusion(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    space_id = _create_space(client, team_id=team_id, user_id=user_id, name="Promote Space")
    conversation_id = _create_conversation(
        client,
        team_id=team_id,
        user_id=user_id,
        title="Promote Conversation",
    )
    message_id = _create_history_message(
        client,
        team_id=team_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    favorite = _create_favorite(
        client,
        team_id=team_id,
        user_id=user_id,
        space_id=space_id,
        conversation_id=conversation_id,
        message_id=message_id,
    )
    favorite_id = favorite["favorite_id"]

    memory_promote = _promote(
        client,
        favorite_id=favorite_id,
        target="memory",
        team_id=team_id,
        user_id=user_id,
        space_id=space_id,
    )
    assert memory_promote.status_code in {200, 201}

    memory_list = client.get(
        "/api/v1/memory/cards",
        params={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
        },
    )
    assert memory_list.status_code == 200
    assert len(memory_list.json()) >= 1

    conclusion_promote = _promote(
        client,
        favorite_id=favorite_id,
        target="conclusion",
        team_id=team_id,
        user_id=user_id,
        space_id=space_id,
    )
    assert conclusion_promote.status_code in {200, 201}


def test_conclusion_confirm_and_archive(client) -> None:
    suffix = uuid4().hex[:8]
    team_id, user_id = _create_team_and_user(client, suffix)
    space_id = _create_space(client, team_id=team_id, user_id=user_id, name="Conclusion Space")

    create_response = client.post(
        "/api/v1/conclusions",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "space_id": space_id,
            "title": "Release decision",
            "topic": "release",
            "content": "Ship Atlas release to pilot customers.",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    conclusion_id = created["conclusion_id"]

    confirm_response = client.post(
        f"/api/v1/conclusions/{conclusion_id}/confirm",
        json={
            "team_id": team_id,
            "user_id": user_id,
        },
    )
    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()
    assert confirmed["status"] in {"confirmed", "effective"}
    assert confirmed.get("doc_sync_document_id")

    archive_response = client.post(
        f"/api/v1/conclusions/{conclusion_id}/archive",
        json={
            "team_id": team_id,
            "user_id": user_id,
        },
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"
