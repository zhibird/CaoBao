from uuid import uuid4


def _create_team(client, team_id: str) -> None:
    response = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Embedding Team",
            "description": "for embedding model tests",
        },
    )
    assert response.status_code == 201


def _create_user(client, team_id: str, user_id: str) -> None:
    response = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": user_id,
            "role": "member",
        },
    )
    assert response.status_code == 201


def test_embedding_model_config_is_isolated_by_account(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_embedding_{suffix}"
    user_a = f"u_embedding_a_{suffix}"
    user_b = f"u_embedding_b_{suffix}"

    _create_team(client, team_id)
    _create_user(client, team_id, user_a)
    _create_user(client, team_id, user_b)

    upsert = client.post(
        "/api/v1/embedding/models",
        json={
            "team_id": team_id,
            "user_id": user_a,
            "model_name": "text-embedding-3-small",
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-embedding-account-a",
        },
    )
    assert upsert.status_code == 200
    body = upsert.json()
    assert body["model_name"] == "text-embedding-3-small"
    assert body["provider"] == "openai"
    assert body["base_url"] == "https://api.openai.com/v1"
    assert body["has_api_key"] is True
    assert body["masked_api_key"] != "sk-embedding-account-a"

    list_a = client.get(
        "/api/v1/embedding/models",
        params={"team_id": team_id, "user_id": user_a},
    )
    assert list_a.status_code == 200
    assert len(list_a.json()["items"]) == 1
    assert list_a.json()["items"][0]["model_name"] == "text-embedding-3-small"

    list_b = client.get(
        "/api/v1/embedding/models",
        params={"team_id": team_id, "user_id": user_b},
    )
    assert list_b.status_code == 200
    assert list_b.json()["items"] == []


def test_embedding_model_config_can_be_deleted(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_embedding_del_{suffix}"
    user_id = f"u_embedding_del_{suffix}"

    _create_team(client, team_id)
    _create_user(client, team_id, user_id)

    upsert = client.post(
        "/api/v1/embedding/models",
        json={
            "team_id": team_id,
            "user_id": user_id,
            "model_name": "emb-2026-02",
            "provider": "volcengine",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "api_key": "embedding-key-delete",
        },
    )
    assert upsert.status_code == 200

    delete = client.delete(
        "/api/v1/embedding/models/emb-2026-02",
        params={"team_id": team_id, "user_id": user_id},
    )
    assert delete.status_code == 204

    list_after = client.get(
        "/api/v1/embedding/models",
        params={"team_id": team_id, "user_id": user_id},
    )
    assert list_after.status_code == 200
    assert list_after.json()["items"] == []
