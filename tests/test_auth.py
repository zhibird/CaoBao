from datetime import timezone
from uuid import uuid4

from app.db.session import SessionLocal
from app.models.user import User


def test_register_creates_personal_workspace_and_sets_auth_cookies(client) -> None:
    client.cookies.clear()
    suffix = uuid4().hex[:8]
    user_id = f"auth_{suffix}"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "user_id": user_id,
            "display_name": "Auth User",
            "password": "Str0ngPass!",
            "confirm_password": "Str0ngPass!",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == user_id
    assert body["team_id"] == user_id
    assert body["display_name"] == "Auth User"
    assert response.cookies.get("caibao_access_token")
    assert response.cookies.get("caibao_refresh_token")
    set_cookie_headers = response.headers.get_list("set-cookie")
    access_cookie_header = next(
        header
        for header in set_cookie_headers
        if header.startswith("caibao_access_token=")
    )
    refresh_cookie_header = next(
        header
        for header in set_cookie_headers
        if header.startswith("caibao_refresh_token=")
    )
    assert "Max-Age=900" in access_cookie_header
    assert "Max-Age=1209600" in refresh_cookie_header

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user_id"] == user_id
    assert me.json()["team_id"] == user_id


def test_login_rejects_wrong_password(client) -> None:
    client.cookies.clear()
    suffix = uuid4().hex[:8]
    user_id = f"login_{suffix}"

    register = client.post(
        "/api/v1/auth/register",
        json={
            "user_id": user_id,
            "display_name": "Login User",
            "password": "Str0ngPass!",
            "confirm_password": "Str0ngPass!",
        },
    )
    assert register.status_code == 201

    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login",
        json={
            "user_id": user_id,
            "password": "WrongPass!",
        },
    )
    assert login.status_code == 401
    assert login.json()["detail"] == "Invalid credentials."


def test_me_rejects_token_after_password_timestamp_changes_within_same_second(client) -> None:
    suffix = uuid4().hex[:8]
    user_id = f"stamp_{suffix}"
    register = client.post(
        "/api/v1/auth/register",
        json={
            "user_id": user_id,
            "display_name": "Stamp User",
            "password": "Str0ngPass!",
            "confirm_password": "Str0ngPass!",
        },
    )
    assert register.status_code == 201

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert user.password_updated_at is not None
        updated_at = user.password_updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        microsecond = 999998 if updated_at.microsecond >= 999999 else updated_at.microsecond + 1
        user.password_updated_at = updated_at.replace(microsecond=microsecond)
        db.add(user)
        db.commit()

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401
    assert me.json()["detail"] == "Authentication required."


def test_me_returns_403_for_inactive_user(client) -> None:
    suffix = uuid4().hex[:8]
    user_id = f"inactive_{suffix}"
    register = client.post(
        "/api/v1/auth/register",
        json={
            "user_id": user_id,
            "display_name": "Inactive User",
            "password": "Str0ngPass!",
            "confirm_password": "Str0ngPass!",
        },
    )
    assert register.status_code == 201

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.is_active = False
        db.add(user)
        db.commit()

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 403
    assert me.json()["detail"] == "User account is inactive."


def test_refresh_rotates_refresh_cookie_and_rejects_reuse(client) -> None:
    client.cookies.clear()
    suffix = uuid4().hex[:8]
    user_id = f"refresh_{suffix}"

    register = client.post(
        "/api/v1/auth/register",
        json={
            "user_id": user_id,
            "display_name": "Refresh User",
            "password": "Str0ngPass!",
            "confirm_password": "Str0ngPass!",
        },
    )
    assert register.status_code == 201
    original_refresh = register.cookies.get("caibao_refresh_token")
    assert original_refresh

    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    rotated_refresh = refresh.cookies.get("caibao_refresh_token")
    assert rotated_refresh
    assert rotated_refresh != original_refresh

    client.cookies.set("caibao_refresh_token", original_refresh)
    reuse = client.post("/api/v1/auth/refresh")
    assert reuse.status_code == 401
    assert reuse.json()["detail"] == "Authentication required."


def test_logout_revokes_refresh_session_and_clears_auth_cookies(client) -> None:
    client.cookies.clear()
    suffix = uuid4().hex[:8]
    user_id = f"logout_{suffix}"

    register = client.post(
        "/api/v1/auth/register",
        json={
            "user_id": user_id,
            "display_name": "Logout User",
            "password": "Str0ngPass!",
            "confirm_password": "Str0ngPass!",
        },
    )
    assert register.status_code == 201
    original_refresh = register.cookies.get("caibao_refresh_token")
    assert original_refresh

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert client.cookies.get("caibao_access_token") is None
    assert client.cookies.get("caibao_refresh_token") is None

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401

    client.cookies.set("caibao_refresh_token", original_refresh)
    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 401


def test_change_password_revokes_existing_session_and_requires_new_login(client) -> None:
    client.cookies.clear()
    suffix = uuid4().hex[:8]
    user_id = f"pwd_{suffix}"

    register = client.post(
        "/api/v1/auth/register",
        json={
            "user_id": user_id,
            "display_name": "Password User",
            "password": "Str0ngPass!",
            "confirm_password": "Str0ngPass!",
        },
    )
    assert register.status_code == 201
    original_refresh = register.cookies.get("caibao_refresh_token")
    assert original_refresh

    change = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "Str0ngPass!",
            "new_password": "N3wPassw0rd!",
            "confirm_new_password": "N3wPassw0rd!",
        },
    )
    assert change.status_code == 204
    assert client.cookies.get("caibao_access_token") is None
    assert client.cookies.get("caibao_refresh_token") is None

    client.cookies.set("caibao_refresh_token", original_refresh)
    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 401
    assert refresh.json()["detail"] == "Authentication required."

    login_old = client.post(
        "/api/v1/auth/login",
        json={"user_id": user_id, "password": "Str0ngPass!"},
    )
    assert login_old.status_code == 401
    assert login_old.json()["detail"] == "Invalid credentials."

    login_new = client.post(
        "/api/v1/auth/login",
        json={"user_id": user_id, "password": "N3wPassw0rd!"},
    )
    assert login_new.status_code == 200
    assert login_new.json()["user_id"] == user_id
