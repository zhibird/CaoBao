from uuid import uuid4


def test_create_team_and_user(client) -> None:
    suffix = uuid4().hex[:8]
    team_id = f"team_{suffix}"
    user_id = f"u_{suffix}"

    team_response = client.post(
        "/api/v1/teams",
        json={
            "team_id": team_id,
            "name": "Operations",
            "description": "MVP team",
        },
    )
    assert team_response.status_code == 201
    assert team_response.json()["team_id"] == team_id

    user_response = client.post(
        "/api/v1/users",
        json={
            "user_id": user_id,
            "team_id": team_id,
            "display_name": "Bob",
            "role": "member",
        },
    )
    assert user_response.status_code == 201
    assert user_response.json()["team_id"] == team_id

    get_user_response = client.get(f"/api/v1/users/{user_id}")
    assert get_user_response.status_code == 200
    assert get_user_response.json()["display_name"] == "Bob"
