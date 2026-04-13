from app.core.config import reload_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("Str0ngPass!")

    assert password_hash != "Str0ngPass!"
    assert verify_password("Str0ngPass!", password_hash) is True
    assert verify_password("WrongPass!", password_hash) is False


def test_access_token_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///security.db")
    monkeypatch.setenv("AUTH_JWT_SECRET", "security-secret")
    settings = reload_settings()

    token = create_access_token(
        subject="user_123",
        team_id="team_123",
        role="member",
        password_timestamp=1710000000,
        settings=settings,
    )
    payload = decode_access_token(token, settings=settings)

    assert payload["sub"] == "user_123"
    assert payload["team_id"] == "team_123"
    assert payload["role"] == "member"
    assert payload["pwd_ts"] == 1710000000


def test_refresh_token_hash_is_stable() -> None:
    raw = "refresh-token-value"
    assert hash_refresh_token(raw) == hash_refresh_token(raw)
