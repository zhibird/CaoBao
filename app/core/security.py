from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import jwt
from passlib.context import CryptContext

from app.core.config import Settings

_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw_password: str) -> str:
    return _password_context.hash(raw_password)


def verify_password(raw_password: str, password_hash: str | None) -> bool:
    return bool(password_hash) and _password_context.verify(raw_password, password_hash)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def create_access_token(
    *,
    subject: str,
    team_id: str,
    role: str,
    password_timestamp: int,
    settings: Settings,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.auth_access_token_ttl_minutes)
    payload = {
        "sub": subject,
        "team_id": team_id,
        "role": role,
        "pwd_ts": password_timestamp,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)


def decode_access_token(token: str, *, settings: Settings) -> dict[str, object]:
    return jwt.decode(token, settings.auth_jwt_secret, algorithms=[settings.auth_jwt_algorithm])
