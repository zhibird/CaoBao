from uuid import uuid4

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def register_workspace_user(client, *, prefix: str, display_name: str) -> tuple[str, str]:
    suffix = uuid4().hex[:8]
    user_id = f"{prefix}_{suffix}"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "user_id": user_id,
            "display_name": display_name,
            "password": "Str0ngPass!",
            "confirm_password": "Str0ngPass!",
        },
    )
    assert response.status_code == 201
    body = response.json()
    return body["team_id"], body["user_id"]


def register_workspace_user_in_team(
    client,
    *,
    team_id: str,
    prefix: str,
    display_name: str,
    password: str = "Str0ngPass!",
) -> tuple[str, str]:
    suffix = uuid4().hex[:8]
    user_id = f"{prefix}_{suffix}"

    with SessionLocal() as db:
        assert db.get(User, user_id) is None
        user = User(
            user_id=user_id,
            team_id=team_id,
            display_name=display_name,
            role="member",
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(user)
        db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "user_id": user_id,
            "password": password,
        },
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["team_id"] == team_id
    assert body["user_id"] == user_id
    return body["team_id"], body["user_id"]
