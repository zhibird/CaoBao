from uuid import uuid4

from tests.auth_helpers import register_workspace_user


def _create_conversation(client, *, title: str) -> dict:
    response = client.post(
        "/api/v1/conversations",
        json={"title": title},
    )
    assert response.status_code == 201
    return response.json()


def _create_history_message(
    client,
    *,
    conversation_id: str,
) -> str:
    echo_response = client.post(
        "/api/v1/chat/echo",
        json={
            "conversation_id": conversation_id,
            "message": "Snapshot this message.",
        },
    )
    assert echo_response.status_code == 200

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


def _create_favorite(
    client,
    *,
    space_id: str,
    message_id: str,
) -> dict:
    response = client.post(
        "/api/v1/favorites/answers",
        json={
            "space_id": space_id,
            "message_id": message_id,
            "title": "Saved Answer",
            "note": "keep this one",
            "tags": ["phase3", "favorite"],
        },
    )
    assert response.status_code == 201
    return response.json()


def _promote(client, *, favorite_id: str, target: str, space_id: str):
    url = f"/api/v1/favorites/answers/{favorite_id}/promote-to-{target}"
    return client.post(url, json={"space_id": space_id})


def test_favorites_and_conclusions_require_authenticated_user(client) -> None:
    client.cookies.clear()

    favorites_response = client.get(
        "/api/v1/favorites/answers",
        params={"space_id": "space_123", "limit": 20},
    )
    assert favorites_response.status_code == 401

    conclusions_response = client.get(
        "/api/v1/conclusions",
        params={"space_id": "space_123", "limit": 20},
    )
    assert conclusions_response.status_code == 401


def test_favorites_crud_and_access_boundary(client) -> None:
    suffix = uuid4().hex[:8]
    owner_team_id, owner_user_id = register_workspace_user(
        client,
        prefix=f"phase3_owner_{suffix}",
        display_name="Phase3 Owner",
    )

    conversation = _create_conversation(client, title="Favorites Conversation")
    space_id = conversation["space_id"]
    conversation_id = conversation["conversation_id"]
    message_id = _create_history_message(
        client,
        conversation_id=conversation_id,
    )

    favorite = _create_favorite(
        client,
        space_id=space_id,
        message_id=message_id,
    )
    favorite_id = favorite["favorite_id"]

    list_response = client.get(
        "/api/v1/favorites/answers",
        params={"space_id": space_id},
    )
    assert list_response.status_code == 200
    listed = list_response.json()
    assert any(item["favorite_id"] == favorite_id for item in listed)

    patch_response = client.patch(
        f"/api/v1/favorites/answers/{favorite_id}",
        json={"title": "Saved Answer Updated"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Saved Answer Updated"

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    intruder_team_id, intruder_user_id = register_workspace_user(
        client,
        prefix=f"phase3_intruder_{suffix}",
        display_name="Intruder",
    )
    assert intruder_team_id != owner_team_id
    assert intruder_user_id != owner_user_id

    forbidden = client.get(
        "/api/v1/favorites/answers",
        params={"space_id": space_id},
    )
    assert forbidden.status_code == 404
    assert forbidden.json()["detail"] == f"Space '{space_id}' not found."

    delete_response = client.delete(f"/api/v1/favorites/answers/{favorite_id}")
    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == f"Favorite '{favorite_id}' not found."


def test_promote_favorite_to_memory_and_conclusion(client) -> None:
    suffix = uuid4().hex[:8]
    register_workspace_user(
        client,
        prefix=f"phase3_promote_{suffix}",
        display_name="Phase3 Promoter",
    )
    conversation = _create_conversation(client, title="Promote Conversation")
    space_id = conversation["space_id"]
    conversation_id = conversation["conversation_id"]
    message_id = _create_history_message(
        client,
        conversation_id=conversation_id,
    )

    favorite = _create_favorite(
        client,
        space_id=space_id,
        message_id=message_id,
    )
    favorite_id = favorite["favorite_id"]

    memory_promote = _promote(
        client,
        favorite_id=favorite_id,
        target="memory",
        space_id=space_id,
    )
    assert memory_promote.status_code in {200, 201}

    memory_list = client.get(
        "/api/v1/memory/cards",
        params={"space_id": space_id},
    )
    assert memory_list.status_code == 200
    assert len(memory_list.json()) >= 1

    conclusion_promote = _promote(
        client,
        favorite_id=favorite_id,
        target="conclusion",
        space_id=space_id,
    )
    assert conclusion_promote.status_code in {200, 201}

    conclusion_list = client.get(
        "/api/v1/conclusions",
        params={"space_id": space_id, "limit": 20},
    )
    assert conclusion_list.status_code == 200
    assert len(conclusion_list.json()) >= 1


def test_promoted_assets_can_be_removed_again(client) -> None:
    suffix = uuid4().hex[:8]
    register_workspace_user(
        client,
        prefix=f"phase3_reversible_{suffix}",
        display_name="Phase3 Reversible User",
    )
    conversation = _create_conversation(client, title="Reversible Workspace")
    space_id = conversation["space_id"]
    conversation_id = conversation["conversation_id"]
    message_id = _create_history_message(
        client,
        conversation_id=conversation_id,
    )

    favorite = _create_favorite(
        client,
        space_id=space_id,
        message_id=message_id,
    )
    favorite_id = favorite["favorite_id"]

    memory_promote = _promote(
        client,
        favorite_id=favorite_id,
        target="memory",
        space_id=space_id,
    )
    assert memory_promote.status_code in {200, 201}
    memory_id = memory_promote.json()["result"]["memory_id"]
    assert memory_id

    delete_memory = client.delete(f"/api/v1/memory/cards/{memory_id}")
    assert delete_memory.status_code == 204

    memory_list = client.get(
        "/api/v1/memory/cards",
        params={"space_id": space_id},
    )
    assert memory_list.status_code == 200
    assert all(item["memory_id"] != memory_id for item in memory_list.json())

    conclusion_promote = _promote(
        client,
        favorite_id=favorite_id,
        target="conclusion",
        space_id=space_id,
    )
    assert conclusion_promote.status_code in {200, 201}
    conclusion_id = conclusion_promote.json()["result"]["conclusion_id"]
    assert conclusion_id

    archive_conclusion = client.post(
        f"/api/v1/conclusions/{conclusion_id}/archive",
        json={},
    )
    assert archive_conclusion.status_code == 200
    assert archive_conclusion.json()["status"] == "archived"

    library_create = client.post(
        "/api/v1/documents/import",
        json={
            "space_id": space_id,
            "source_name": f"favorite-{message_id}.md",
            "content_type": "md",
            "content": "# 收藏沉淀\n\n这是一条可删除的资料库卡片。",
            "meta": {
                "source_message_id": message_id,
                "capture_kind": "favorite_answer",
                "favorite_id": favorite_id,
            },
        },
    )
    assert library_create.status_code == 201
    library_document_id = library_create.json()["document_id"]

    library_list = client.get(
        "/api/v1/library/documents",
        params={"space_id": space_id},
    )
    assert library_list.status_code == 200
    assert any(item["document_id"] == library_document_id for item in library_list.json())

    delete_library_document = client.delete(f"/api/v1/documents/{library_document_id}")
    assert delete_library_document.status_code == 204

    library_list_after_delete = client.get(
        "/api/v1/library/documents",
        params={"space_id": space_id},
    )
    assert library_list_after_delete.status_code == 200
    assert all(item["document_id"] != library_document_id for item in library_list_after_delete.json())


def test_conclusion_confirm_and_archive(client) -> None:
    suffix = uuid4().hex[:8]
    register_workspace_user(
        client,
        prefix=f"phase3_conclusion_{suffix}",
        display_name="Phase3 Conclusion User",
    )
    conversation = _create_conversation(client, title="Conclusion Space")
    space_id = conversation["space_id"]

    create_response = client.post(
        "/api/v1/conclusions",
        json={
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
        json={},
    )
    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()
    assert confirmed["status"] in {"confirmed", "effective"}
    assert confirmed.get("doc_sync_document_id")

    archive_response = client.post(
        f"/api/v1/conclusions/{conclusion_id}/archive",
        json={},
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"
