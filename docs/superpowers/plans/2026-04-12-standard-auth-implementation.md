# Standard Auth Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a full password-based login and authorization loop for the main CaiBao workspace with cookie-based access/refresh tokens, protected APIs, and frontend session recovery.

**Architecture:** Add a focused auth slice around the existing FastAPI app: config + security helpers + refresh-session persistence + auth service + auth routes. Keep the business service layer mostly intact and migrate API route handlers to derive `team_id` and `user_id` from the authenticated user, while the frontend switches from local bootstrap identity to `/auth/me`-driven session state.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, PyJWT, passlib[bcrypt], vanilla JS, pytest, TestClient

---

## Preflight

- Work in a dedicated worktree because `README.md` and `changelogs/0.15.0.md` are already dirty in the current workspace.
- Suggested commands:

```powershell
git worktree add .worktrees/standard-auth -b codex/standard-auth
Set-Location .worktrees/standard-auth
```

- Keep the existing `.venv` if it already works for the repo. Reinstall dependencies after `requirements.txt` changes:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## File Map

### Create

- `app/core/security.py`: password hashing, JWT mint/decode, refresh token generation and hashing
- `app/models/auth_refresh_session.py`: refresh token persistence model
- `app/schemas/auth.py`: register/login/me/change-password request and response models
- `app/services/auth_service.py`: registration, login, refresh rotation, logout, current-user resolution, password change
- `app/api/routes/auth.py`: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`, `/auth/change-password`
- `tests/test_security.py`: password and token helper tests
- `tests/test_auth.py`: integration tests for auth cookies and session lifecycle
- `tests/auth_helpers.py`: authenticated test bootstrap helpers for route tests
- `tests/test_authenticated_routes.py`: anonymous `401` smoke coverage for protected route groups
- `alembic/versions/20260412_00_add_standard_auth.py`: schema migration for auth columns and refresh session table

### Modify

- `requirements.txt`: add auth libraries
- `.env.example`: add auth env vars
- `app/core/config.py`: add auth settings
- `app/models/user.py`: add password/auth state columns
- `app/models/__init__.py`: expose new auth model to metadata discovery
- `app/api/deps.py`: add auth service factory and current-user dependencies
- `app/api/router.py`: register auth router
- `app/api/routes/conversation.py`: derive identity from authenticated user
- `app/api/routes/chat.py`: derive identity from authenticated user
- `app/api/routes/document.py`: derive identity from authenticated user
- `app/api/routes/retrieval.py`: derive identity from authenticated user
- `app/api/routes/space.py`: derive identity from authenticated user
- `app/api/routes/library.py`: derive identity from authenticated user
- `app/api/routes/memory.py`: derive identity from authenticated user
- `app/api/routes/favorite.py`: derive identity from authenticated user
- `app/api/routes/conclusion.py`: derive identity from authenticated user
- `app/api/routes/llm_model.py`: derive identity from authenticated user
- `app/api/routes/embedding_model.py`: derive identity from authenticated user
- `tests/conftest.py`: auth env vars and cookie reset fixture
- `tests/test_config.py`: auth setting defaults
- `tests/test_migrations.py`: new migration head revision and schema assertions
- `tests/test_conversation.py`: register/login helper instead of bootstrap identity
- `tests/test_chat.py`: register/login helper instead of bootstrap identity
- `tests/test_document.py`: register/login helper for protected routes
- `tests/test_retrieval.py`: register/login helper for protected routes
- `tests/test_spaces_and_library.py`: register/login helper for protected routes
- `tests/test_favorites_and_conclusions.py`: register/login helper for protected routes
- `tests/test_llm_model.py`: register/login helper for protected routes
- `tests/test_embedding_model.py`: register/login helper for protected routes
- `tests/test_web_assets.py`: expect login/register UX and `/auth/*` bootstrap flow
- `app/web/index.html`: replace workspace bootstrap modal with login/register modal
- `app/web/styles.css`: auth tab and password field styling updates
- `app/web/app.js`: session bootstrap, login/register/logout, refresh-once retry, remove workspace ensure flow

## Compatibility Rules

- Keep `password_hash` and `password_updated_at` nullable in the first migration so pre-auth rows and developer-created users do not break existing data loads. The auth service must reject login when `password_hash` is missing.
- Keep existing request schemas that still include `team_id` and `user_id` in phase 1. Protected route handlers must ignore client-supplied identity and overwrite it from `current_user`.
- Leave `/web/admin.html` and `X-Dev-Admin-Token` unchanged.

### Task 1: Add Auth Configuration and Dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `app/core/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing config test**

```python
def test_settings_expose_auth_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///auth-config.db")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-auth-secret")

    settings = Settings(_env_file=None)

    assert settings.auth_jwt_secret == "test-auth-secret"
    assert settings.auth_jwt_algorithm == "HS256"
    assert settings.auth_access_token_ttl_minutes == 15
    assert settings.auth_refresh_token_ttl_days == 14
    assert settings.auth_access_cookie_name == "caibao_access_token"
    assert settings.auth_refresh_cookie_name == "caibao_refresh_token"
    assert settings.auth_cookie_samesite == "lax"
    assert settings.auth_cookie_secure is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_config.py::test_settings_expose_auth_defaults -v
```

Expected: FAIL with `AttributeError` or validation output because the new auth settings do not exist yet.

- [ ] **Step 3: Write the minimal config and dependency changes**

`requirements.txt`

```text
fastapi==0.116.1
uvicorn==0.35.0
pydantic-settings==2.11.0
sqlalchemy==2.0.44
alembic==1.14.1
psycopg[binary]==3.3.3
pytest==8.4.2
httpx==0.28.1
pypdf==5.9.0
Pillow==11.3.0
pytesseract==0.3.13
python-multipart==0.0.20
PyJWT==2.10.1
passlib[bcrypt]==1.7.4
```

`app/core/config.py`

```python
class Settings(BaseSettings):
    app_name: str = "CaiBao"
    app_version: str = "0.13.0"
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str

    auth_jwt_secret: str = "dev-auth-secret-change-me"
    auth_jwt_algorithm: str = "HS256"
    auth_access_token_ttl_minutes: int = 15
    auth_refresh_token_ttl_days: int = 14
    auth_cookie_secure: bool = False
    auth_cookie_domain: str | None = None
    auth_cookie_samesite: str = "lax"
    auth_access_cookie_name: str = "caibao_access_token"
    auth_refresh_cookie_name: str = "caibao_refresh_token"

    dev_admin_enabled: bool = True
    dev_admin_account_id: str = "dev_admin"
    dev_admin_display_name: str = "Developer Admin"
    dev_admin_token: str = "dev-admin-token"
```

`.env.example`

```dotenv
AUTH_JWT_SECRET=change-me-before-production
AUTH_JWT_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_TTL_MINUTES=15
AUTH_REFRESH_TOKEN_TTL_DAYS=14
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
AUTH_ACCESS_COOKIE_NAME=caibao_access_token
AUTH_REFRESH_COOKIE_NAME=caibao_refresh_token
```

- [ ] **Step 4: Run the config tests to verify they pass**

Run:

```powershell
pytest tests/test_config.py -v
```

Expected: PASS with the new auth settings test green and the existing config tests still green.

- [ ] **Step 5: Commit**

```powershell
git add requirements.txt .env.example app/core/config.py tests/test_config.py
git commit -m "chore: add auth configuration defaults"
```

### Task 2: Add Auth Persistence and Migration

**Files:**
- Modify: `app/models/user.py`
- Create: `app/models/auth_refresh_session.py`
- Modify: `app/models/__init__.py`
- Create: `alembic/versions/20260412_00_add_standard_auth.py`
- Test: `tests/test_migrations.py`

- [ ] **Step 1: Write the failing migration test**

```python
def test_auth_migration_adds_auth_tables_and_user_columns(tmp_path) -> None:
    db_file = tmp_path / "auth.db"
    database_url = _sqlite_database_url(db_file)
    config = _make_alembic_config(database_url)

    command.upgrade(config, "head")

    engine = _create_engine(database_url)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            users_columns = {col["name"] for col in inspector.get_columns("users")}
            refresh_columns = {col["name"] for col in inspector.get_columns("auth_refresh_sessions")}
    finally:
        engine.dispose()

    assert {"password_hash", "is_active", "password_updated_at"} <= users_columns
    assert {"session_id", "user_id", "refresh_token_hash", "expires_at", "revoked_at"} <= refresh_columns
```

Also update the migration head constant:

```python
HEAD_REVISION = "20260412_00"
EXPECTED_TABLES = {
    "teams",
    "users",
    "project_spaces",
    "memory_cards",
    "answer_favorites",
    "conclusions",
    "auth_refresh_sessions",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_migrations.py::test_auth_migration_adds_auth_tables_and_user_columns -v
```

Expected: FAIL because the migration head and the auth tables/columns do not exist yet.

- [ ] **Step 3: Write the minimal model and migration changes**

`app/models/user.py`

```python
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.team_id"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    password_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

`app/models/auth_refresh_session.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuthRefreshSession(Base):
    __tablename__ = "auth_refresh_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship()
```

`app/models/__init__.py`

```python
from . import (  # noqa: F401
    answer_favorite,
    auth_refresh_session,
    chat_history,
    chunk_embedding,
    conclusion,
    conversation,
    document,
    document_chunk,
    embedding_model_config,
    incident,
    llm_model_config,
    memory_card,
    memory_card_embedding,
    project_space,
    team,
    user,
)
```

`alembic/versions/20260412_00_add_standard_auth.py`

```python
from alembic import op
import sqlalchemy as sa

revision = "20260412_00"
down_revision = "20260330_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")))
    op.add_column("users", sa.Column("password_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "auth_refresh_sessions",
        sa.Column("session_id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_session_id", sa.String(length=36), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_auth_refresh_sessions_user_id", "auth_refresh_sessions", ["user_id"])
    op.create_index("ix_auth_refresh_sessions_refresh_token_hash", "auth_refresh_sessions", ["refresh_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_auth_refresh_sessions_refresh_token_hash", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_user_id", table_name="auth_refresh_sessions")
    op.drop_table("auth_refresh_sessions")
    op.drop_column("users", "password_updated_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "password_hash")
```

- [ ] **Step 4: Run migration tests to verify they pass**

Run:

```powershell
pytest tests/test_migrations.py -v
```

Expected: PASS with the new head revision, expected tables, and auth column assertions green.

- [ ] **Step 5: Commit**

```powershell
git add app/models/user.py app/models/auth_refresh_session.py app/models/__init__.py alembic/versions/20260412_00_add_standard_auth.py tests/test_migrations.py
git commit -m "feat: add auth persistence schema"
```

### Task 3: Add Security Helpers for Passwords and Tokens

**Files:**
- Create: `app/core/security.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Write the failing security tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_security.py -v
```

Expected: FAIL because `app.core.security` does not exist yet.

- [ ] **Step 3: Write the minimal security helper implementation**

`app/core/security.py`

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
pytest tests/test_security.py -v
```

Expected: PASS for password hash verification, token round-trip, and refresh token hashing.

- [ ] **Step 5: Commit**

```powershell
git add app/core/security.py tests/test_security.py
git commit -m "feat: add auth security helpers"
```

### Task 4: Implement Registration, Login, and Current Session APIs

**Files:**
- Create: `app/schemas/auth.py`
- Create: `app/services/auth_service.py`
- Create: `app/api/routes/auth.py`
- Modify: `app/api/deps.py`
- Modify: `app/api/router.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write the failing auth API tests**

```python
from uuid import uuid4


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_auth.py::test_register_creates_personal_workspace_and_sets_auth_cookies -v
pytest tests/test_auth.py::test_login_rejects_wrong_password -v
```

Expected: FAIL with `404` because `/api/v1/auth/*` routes do not exist yet.

- [ ] **Step 3: Write the minimal auth route, service, and fixture implementation**

`tests/conftest.py`

```python
os.environ["AUTH_JWT_SECRET"] = "test-auth-secret"


@pytest.fixture(autouse=True)
def clear_client_cookies(client: TestClient):
    client.cookies.clear()
    yield
    client.cookies.clear()
```

`app/schemas/auth.py`

```python
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class AuthSessionResponse(BaseModel):
    user_id: str
    team_id: str
    team_name: str
    display_name: str
    role: str
    is_active: bool
```

`app/services/auth_service.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import DomainValidationError, EntityConflictError, EntityNotFoundError
from app.core.security import create_access_token, generate_refresh_token, hash_password, hash_refresh_token, verify_password
from app.models.auth_refresh_session import AuthRefreshSession
from app.models.team import Team
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


@dataclass
class AuthResult:
    user: User
    team_name: str
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def register(self, payload: RegisterRequest, *, user_agent: str | None, ip_address: str | None) -> AuthResult:
        if payload.password != payload.confirm_password:
            raise DomainValidationError("Passwords do not match.")
        if self.db.get(User, payload.user_id) is not None:
            raise EntityConflictError(f"User '{payload.user_id}' already exists.")

        team = Team(team_id=payload.user_id, name=payload.display_name, description=None)
        user = User(
            user_id=payload.user_id,
            team_id=payload.user_id,
            display_name=payload.display_name,
            role="member",
            password_hash=hash_password(payload.password),
            is_active=True,
            password_updated_at=datetime.now(timezone.utc),
        )
        self.db.add(team)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self._issue_session(user=user, team_name=team.name, user_agent=user_agent, ip_address=ip_address)

    def login(self, payload: LoginRequest, *, user_agent: str | None, ip_address: str | None) -> AuthResult:
        user = self.db.get(User, payload.user_id)
        if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
            raise DomainValidationError("Invalid credentials.")
        team = self.db.get(Team, user.team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{user.team_id}' not found.")
        return self._issue_session(user=user, team_name=team.name, user_agent=user_agent, ip_address=ip_address)

    def _issue_session(self, *, user: User, team_name: str, user_agent: str | None, ip_address: str | None) -> AuthResult:
        refresh_token = generate_refresh_token()
        now = datetime.now(timezone.utc)
        session = AuthRefreshSession(
            session_id=str(uuid4()),
            user_id=user.user_id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            issued_at=now,
            expires_at=now + timedelta(days=self.settings.auth_refresh_token_ttl_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(session)
        self.db.commit()
        password_timestamp = int((user.password_updated_at or now).timestamp())
        access_token = create_access_token(
            subject=user.user_id,
            team_id=user.team_id,
            role=user.role,
            password_timestamp=password_timestamp,
            settings=self.settings,
        )
        return AuthResult(user=user, team_name=team_name, access_token=access_token, refresh_token=refresh_token)
```

`app/api/deps.py`

```python
from fastapi import Depends, HTTPException, Request, status

from app.services.auth_service import AuthService


def get_auth_service(db: Session = Depends(get_db_session)) -> AuthService:
    return AuthService(db=db, settings=reload_settings())


def require_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return auth_service.get_current_user_from_request(request)
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def require_current_active_user(
    current_user = Depends(require_current_user),
):
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")
    return current_user
```

`app/api/routes/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_auth_service, require_current_active_user
from app.core.exceptions import DomainValidationError, EntityConflictError
from app.schemas.auth import AuthSessionResponse, LoginRequest, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    try:
        result = auth_service.register(
            payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        auth_service.write_auth_cookies(response, access_token=result.access_token, refresh_token=result.refresh_token)
        return AuthSessionResponse(
            user_id=result.user.user_id,
            team_id=result.user.team_id,
            team_name=result.team_name,
            display_name=result.user.display_name,
            role=result.user.role,
            is_active=result.user.is_active,
        )
    except (DomainValidationError, EntityConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/login", response_model=AuthSessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    try:
        result = auth_service.login(
            payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        auth_service.write_auth_cookies(response, access_token=result.access_token, refresh_token=result.refresh_token)
        return AuthSessionResponse(
            user_id=result.user.user_id,
            team_id=result.user.team_id,
            team_name=result.team_name,
            display_name=result.user.display_name,
            role=result.user.role,
            is_active=result.user.is_active,
        )
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/me", response_model=AuthSessionResponse)
def me(
    current_user = Depends(require_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    team_name = auth_service.get_team_name(current_user.team_id)
    return AuthSessionResponse(
        user_id=current_user.user_id,
        team_id=current_user.team_id,
        team_name=team_name,
        display_name=current_user.display_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )
```

`app/api/router.py`

```python
from app.api.routes.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(admin_router, tags=["admin"])
```

Add the missing request cookie reader methods to `AuthService` before running tests:

```python
from fastapi import Request, Response
import jwt

    def get_current_user_from_request(self, request: Request) -> User:
        raw_token = request.cookies.get(self.settings.auth_access_cookie_name)
        if not raw_token:
            raise DomainValidationError("Authentication required.")
        try:
            payload = decode_access_token(raw_token, settings=self.settings)
        except jwt.PyJWTError as exc:
            raise DomainValidationError("Authentication required.") from exc
        user = self.db.get(User, str(payload["sub"]))
        if user is None:
            raise DomainValidationError("Authentication required.")
        password_timestamp = int((user.password_updated_at or datetime.fromtimestamp(0, timezone.utc)).timestamp())
        if int(payload.get("pwd_ts", 0)) != password_timestamp:
            raise DomainValidationError("Authentication required.")
        return user

    def get_team_name(self, team_id: str) -> str:
        team = self.db.get(Team, team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{team_id}' not found.")
        return team.name

    def write_auth_cookies(self, response: Response, *, access_token: str, refresh_token: str) -> None:
        response.set_cookie(
            key=self.settings.auth_access_cookie_name,
            value=access_token,
            httponly=True,
            secure=self.settings.auth_cookie_secure,
            samesite=self.settings.auth_cookie_samesite,
            domain=self.settings.auth_cookie_domain,
            path="/",
        )
        response.set_cookie(
            key=self.settings.auth_refresh_cookie_name,
            value=refresh_token,
            httponly=True,
            secure=self.settings.auth_cookie_secure,
            samesite=self.settings.auth_cookie_samesite,
            domain=self.settings.auth_cookie_domain,
            path="/",
        )
```

- [ ] **Step 4: Run auth tests to verify they pass**

Run:

```powershell
pytest tests/test_auth.py::test_register_creates_personal_workspace_and_sets_auth_cookies -v
pytest tests/test_auth.py::test_login_rejects_wrong_password -v
```

Expected: PASS for registration, `/auth/me`, and invalid password rejection.

- [ ] **Step 5: Commit**

```powershell
git add app/schemas/auth.py app/services/auth_service.py app/api/routes/auth.py app/api/deps.py app/api/router.py tests/conftest.py tests/test_auth.py
git commit -m "feat: add auth register login and me routes"
```

### Task 5: Implement Refresh Rotation, Logout, and Password Change

**Files:**
- Modify: `app/schemas/auth.py`
- Modify: `app/services/auth_service.py`
- Modify: `app/api/routes/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write the failing session lifecycle tests**

```python
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

    reuse = client.post(
        "/api/v1/auth/refresh",
        cookies={"caibao_refresh_token": original_refresh},
    )
    assert reuse.status_code == 401


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

    change = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "Str0ngPass!",
            "new_password": "N3wPassw0rd!",
            "confirm_new_password": "N3wPassw0rd!",
        },
    )
    assert change.status_code == 204
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_auth.py::test_refresh_rotates_refresh_cookie_and_rejects_reuse -v
pytest tests/test_auth.py::test_change_password_revokes_existing_session_and_requires_new_login -v
```

Expected: FAIL because refresh, logout, and change-password routes are not implemented yet.

- [ ] **Step 3: Write the minimal refresh/logout/password-change implementation**

`app/schemas/auth.py`

```python
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str = Field(min_length=8, max_length=128)
```

`app/services/auth_service.py`

```python
    def refresh(self, *, refresh_token: str | None, user_agent: str | None, ip_address: str | None) -> AuthResult:
        if not refresh_token:
            raise DomainValidationError("Authentication required.")
        token_hash = hash_refresh_token(refresh_token)
        stmt = select(AuthRefreshSession).where(AuthRefreshSession.refresh_token_hash == token_hash)
        session = self.db.scalars(stmt).first()
        now = datetime.now(timezone.utc)
        if session is None or session.revoked_at or session.rotated_at or session.expires_at <= now:
            raise DomainValidationError("Authentication required.")

        user = self.db.get(User, session.user_id)
        if user is None or not user.is_active:
            raise DomainValidationError("Authentication required.")

        team = self.db.get(Team, user.team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{user.team_id}' not found.")

        session.rotated_at = now
        replacement = self._issue_session(user=user, team_name=team.name, user_agent=user_agent, ip_address=ip_address)
        newest_session = self.db.scalars(
            select(AuthRefreshSession).where(AuthRefreshSession.refresh_token_hash == hash_refresh_token(replacement.refresh_token))
        ).first()
        if newest_session is not None:
            session.replaced_by_session_id = newest_session.session_id
            self.db.add(session)
            self.db.commit()
        return replacement

    def revoke_refresh_session(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        token_hash = hash_refresh_token(refresh_token)
        session = self.db.scalars(
            select(AuthRefreshSession).where(AuthRefreshSession.refresh_token_hash == token_hash)
        ).first()
        if session is None or session.revoked_at:
            return
        session.revoked_at = datetime.now(timezone.utc)
        self.db.add(session)
        self.db.commit()

    def revoke_all_refresh_sessions_for_user(self, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        sessions = self.db.scalars(
            select(AuthRefreshSession).where(
                AuthRefreshSession.user_id == user_id,
                AuthRefreshSession.revoked_at.is_(None),
            )
        ).all()
        for session in sessions:
            session.revoked_at = now
            self.db.add(session)
        self.db.commit()

    def change_password(self, user: User, *, current_password: str, new_password: str, confirm_new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise DomainValidationError("Invalid credentials.")
        if new_password != confirm_new_password:
            raise DomainValidationError("Passwords do not match.")
        user.password_hash = hash_password(new_password)
        user.password_updated_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.commit()
        self.revoke_all_refresh_sessions_for_user(user.user_id)

    def clear_auth_cookies(self, response: Response) -> None:
        response.delete_cookie(self.settings.auth_access_cookie_name, path="/", domain=self.settings.auth_cookie_domain)
        response.delete_cookie(self.settings.auth_refresh_cookie_name, path="/", domain=self.settings.auth_cookie_domain)
```

`app/api/routes/auth.py`

```python
from app.schemas.auth import ChangePasswordRequest


@router.post("/refresh", response_model=AuthSessionResponse)
def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    try:
        result = auth_service.refresh(
            refresh_token=request.cookies.get(auth_service.settings.auth_refresh_cookie_name),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        auth_service.write_auth_cookies(response, access_token=result.access_token, refresh_token=result.refresh_token)
        return AuthSessionResponse(
            user_id=result.user.user_id,
            team_id=result.user.team_id,
            team_name=result.team_name,
            display_name=result.user.display_name,
            role=result.user.role,
            is_active=result.user.is_active,
        )
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    auth_service.revoke_refresh_session(request.cookies.get(auth_service.settings.auth_refresh_cookie_name))
    auth_service.clear_auth_cookies(response)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    current_user = Depends(require_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    try:
        auth_service.change_password(
            current_user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            confirm_new_password=payload.confirm_new_password,
        )
        auth_service.clear_auth_cookies(response)
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
```

- [ ] **Step 4: Run the auth suite to verify it passes**

Run:

```powershell
pytest tests/test_auth.py -v
```

Expected: PASS for register, login, `/auth/me`, refresh rotation, refresh reuse rejection, and password change invalidation.

- [ ] **Step 5: Commit**

```powershell
git add app/schemas/auth.py app/services/auth_service.py app/api/routes/auth.py tests/test_auth.py
git commit -m "feat: add auth session lifecycle"
```

### Task 6: Protect Conversation and Chat Routes with Current User

**Files:**
- Create: `tests/auth_helpers.py`
- Modify: `app/api/routes/conversation.py`
- Modify: `app/api/routes/chat.py`
- Modify: `tests/test_conversation.py`
- Modify: `tests/test_chat.py`

- [ ] **Step 1: Write the failing protected-route tests**

`tests/auth_helpers.py`

```python
from uuid import uuid4


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
```

Add to `tests/test_conversation.py`

```python
from tests.auth_helpers import register_workspace_user


def test_conversations_require_authenticated_user(client) -> None:
    client.cookies.clear()
    response = client.get("/api/v1/conversations", params={"limit": 20})
    assert response.status_code == 401
```

Update the creation helper to prove the server ignores client identity:

```python
def _create_conversation(client, team_id: str, user_id: str, title: str) -> str:
    response = client.post(
        "/api/v1/conversations",
        json={
            "team_id": "ignored-team",
            "user_id": "ignored-user",
            "title": title,
        },
    )
    assert response.status_code == 201
    assert response.json()["team_id"] == team_id
    assert response.json()["user_id"] == user_id
    return response.json()["conversation_id"]
```

Add to `tests/test_chat.py`

```python
def test_chat_echo_requires_authenticated_session(client) -> None:
    client.cookies.clear()
    response = client.post(
        "/api/v1/chat/echo",
        json={
            "team_id": "ignored-team",
            "user_id": "ignored-user",
            "message": "hello",
        },
    )
    assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest tests/test_conversation.py::test_conversations_require_authenticated_user -v
pytest tests/test_chat.py::test_chat_echo_requires_authenticated_session -v
```

Expected: FAIL because the routes still accept anonymous requests and trust client identity.

- [ ] **Step 3: Write the minimal route protection changes**

`app/api/routes/conversation.py`

```python
from app.api.deps import get_conversation_service, require_current_active_user
from app.models.user import User


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(require_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    item = conversation_service.create(
        team_id=current_user.team_id,
        user_id=current_user.user_id,
        space_id=payload.space_id,
        title=payload.title,
    )
    return ConversationResponse.model_validate(item)


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    current_user: User = Depends(require_current_active_user),
    space_id: str | None = Query(default=None, min_length=1, max_length=36),
    limit: int = Query(default=50, ge=1, le=200),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    conversations = conversation_service.list(
        team_id=current_user.team_id,
        user_id=current_user.user_id,
        space_id=space_id,
        limit=limit,
    )
    return [ConversationResponse.model_validate(item) for item in conversations]
```

`app/api/routes/chat.py`

```python
from app.api.deps import get_action_chat_service, get_chat_history_service, get_chat_service, get_rag_chat_service, require_current_active_user
from app.models.user import User


@router.post("/echo", response_model=ChatEchoResponse)
def chat_echo(
    payload: ChatEchoRequest,
    current_user: User = Depends(require_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatEchoResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    response = chat_service.echo(secured_payload)
    chat_history_service.record_message(
        team_id=secured_payload.team_id,
        user_id=secured_payload.user_id,
        conversation_id=secured_payload.conversation_id,
        channel="echo",
        request_text=secured_payload.message,
        response_text=response.answer,
        request_payload=secured_payload.model_dump(),
        response_payload=response.model_dump(),
    )
    return response


@router.get("/history", response_model=ChatHistoryListResponse)
def chat_history(
    current_user: User = Depends(require_current_active_user),
    conversation_id: str | None = Query(default=None, min_length=1, max_length=36),
    limit: int = Query(default=20, ge=1, le=200),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatHistoryListResponse:
    records = chat_history_service.list_history(
        team_id=current_user.team_id,
        user_id=current_user.user_id,
        conversation_id=conversation_id,
        limit=limit,
    )
    items = [ChatHistoryItem.from_record(item) for item in records]
    return ChatHistoryListResponse.from_result(
        team_id=current_user.team_id,
        user_id=current_user.user_id,
        conversation_id=conversation_id,
        limit=limit,
        items=items,
    )
```

Also update these `chat.py` handlers explicitly:

```python
@router.post("/ask", response_model=ChatAskResponse)
def chat_ask(
    payload: ChatAskRequest,
    current_user: User = Depends(require_current_active_user),
    rag_chat_service: RagChatService = Depends(get_rag_chat_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatAskResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    response = rag_chat_service.ask(secured_payload)
    chat_history_service.record_message(
        team_id=secured_payload.team_id,
        user_id=secured_payload.user_id,
        conversation_id=secured_payload.conversation_id,
        channel="ask",
        request_text=secured_payload.question,
        response_text=response.answer,
        request_payload=secured_payload.model_dump(),
        response_payload=response.model_dump(),
    )
    return response


@router.delete("/history/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_history_message(
    message_id: str,
    current_user: User = Depends(require_current_active_user),
    conversation_id: str | None = Query(default=None, min_length=1, max_length=36),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> None:
    chat_history_service.delete_message(
        message_id=message_id,
        team_id=current_user.team_id,
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )
```

Also update `chat_action(...)` and `edit_chat_history_message(...)` explicitly:

```python
@router.post("/action", response_model=ChatActionResponse)
def chat_action(
    payload: ChatActionRequest,
    current_user: User = Depends(require_current_active_user),
    action_chat_service: ActionChatService = Depends(get_action_chat_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatActionResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    response = action_chat_service.execute(secured_payload)
    chat_history_service.record_message(
        team_id=secured_payload.team_id,
        user_id=secured_payload.user_id,
        conversation_id=secured_payload.conversation_id,
        channel="action",
        request_text=secured_payload.action,
        response_text=str(response.result.get("message", "")).strip() or str(response.result),
        request_payload=secured_payload.model_dump(),
        response_payload=response.model_dump(),
    )
    return response


@router.put("/history/{message_id}", response_model=ChatHistoryItem)
def edit_chat_history_message(
    message_id: str,
    payload: ChatHistoryEditRequest,
    current_user: User = Depends(require_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
    rag_chat_service: RagChatService = Depends(get_rag_chat_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatHistoryItem:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    message = chat_history_service.ensure_latest_message(
        message_id=message_id,
        team_id=secured_payload.team_id,
        user_id=secured_payload.user_id,
    )
    if message.channel == "echo":
        echo_payload = ChatEchoRequest(
            user_id=secured_payload.user_id,
            team_id=secured_payload.team_id,
            conversation_id=message.conversation_id,
            message=secured_payload.request_text,
        )
        echo_response = chat_service.echo(echo_payload)
        updated = chat_history_service.update_message(
            message_id=message_id,
            team_id=secured_payload.team_id,
            user_id=secured_payload.user_id,
            request_text=echo_payload.message,
            response_text=echo_response.answer,
            request_payload=echo_payload.model_dump(),
            response_payload=echo_response.model_dump(),
        )
        return ChatHistoryItem.from_record(updated)

    ask_payload = ChatAskRequest(
        user_id=secured_payload.user_id,
        team_id=secured_payload.team_id,
        conversation_id=message.conversation_id,
        question=secured_payload.request_text,
    )
    ask_response = rag_chat_service.ask(ask_payload, before_message_id=message.message_id)
    updated = chat_history_service.update_message(
        message_id=message_id,
        team_id=secured_payload.team_id,
        user_id=secured_payload.user_id,
        request_text=ask_payload.question,
        response_text=ask_response.answer,
        request_payload=ask_payload.model_dump(),
        response_payload=ask_response.model_dump(),
    )
    return ChatHistoryItem.from_record(updated)
```

Update `tests/test_conversation.py` and `tests/test_chat.py` so every helper creates an authenticated user via `register_workspace_user(...)` instead of `POST /teams` + `POST /users`.

- [ ] **Step 4: Run targeted route tests to verify they pass**

Run:

```powershell
pytest tests/test_conversation.py tests/test_chat.py -v
```

Expected: PASS with anonymous `401` checks green and all existing conversation/chat flows still green under cookie auth.

- [ ] **Step 5: Commit**

```powershell
git add tests/auth_helpers.py app/api/routes/conversation.py app/api/routes/chat.py tests/test_conversation.py tests/test_chat.py
git commit -m "feat: protect conversation and chat routes"
```

### Task 7: Protect Remaining Main Workspace Route Groups

**Files:**
- Create: `tests/test_authenticated_routes.py`
- Modify: `app/api/routes/document.py`
- Modify: `app/api/routes/retrieval.py`
- Modify: `app/api/routes/space.py`
- Modify: `app/api/routes/library.py`
- Modify: `app/api/routes/memory.py`
- Modify: `app/api/routes/favorite.py`
- Modify: `app/api/routes/conclusion.py`
- Modify: `app/api/routes/llm_model.py`
- Modify: `app/api/routes/embedding_model.py`
- Modify: `tests/test_document.py`
- Modify: `tests/test_retrieval.py`
- Modify: `tests/test_spaces_and_library.py`
- Modify: `tests/test_favorites_and_conclusions.py`
- Modify: `tests/test_llm_model.py`
- Modify: `tests/test_embedding_model.py`

- [ ] **Step 1: Write the failing anonymous-access smoke tests**

```python
def test_workspace_routes_require_authentication(client) -> None:
    client.cookies.clear()

    checks = [
        ("get", "/api/v1/llm/models", {"params": {}}),
        ("get", "/api/v1/embedding/models", {"params": {}}),
        ("get", "/api/v1/spaces", {"params": {"limit": 10}}),
        ("get", "/api/v1/chat/history", {"params": {"limit": 10}}),
        ("get", "/api/v1/favorites/answers", {"params": {"limit": 10}}),
        ("get", "/api/v1/memory/cards", {"params": {"limit": 10}}),
    ]

    for method, path, kwargs in checks:
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 401, (method, path, response.status_code)
```

Update one representative success-path test per route cluster to register through auth instead of bootstrapping with `/teams` and `/users` directly.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest tests/test_authenticated_routes.py -v
pytest tests/test_document.py tests/test_retrieval.py tests/test_spaces_and_library.py tests/test_favorites_and_conclusions.py tests/test_llm_model.py tests/test_embedding_model.py -v
```

Expected: FAIL because the listed routes still accept anonymous requests or still depend on explicit `team_id` / `user_id` test setup.

- [ ] **Step 3: Write the minimal route protection changes for the remaining route groups**

Apply `current_user: User = Depends(require_current_active_user)` to every listed route module, and replace every client-supplied identity path with the concrete handler shapes below.

Representative snippets:

`app/api/routes/llm_model.py`

```python
from app.api.deps import get_llm_model_service, require_current_active_user
from app.models.user import User


@router.get("/models", response_model=list[LLMModelResponse])
def list_models(
    current_user: User = Depends(require_current_active_user),
    llm_model_service: LLMModelService = Depends(get_llm_model_service),
) -> list[LLMModelResponse]:
    items = llm_model_service.list_configs(
        team_id=current_user.team_id,
        user_id=current_user.user_id,
    )
    return [
        LLMModelResponse(
            team_id=item.team_id,
            user_id=item.user_id,
            name=item.name,
            provider=item.provider,
            base_url=item.base_url,
            model=item.model,
            is_default=item.is_default,
            created_at=item.created_at,
        )
        for item in items
    ]
```

`app/api/routes/embedding_model.py`

```python
@router.post("/models", response_model=EmbeddingModelResponse, status_code=status.HTTP_201_CREATED)
def create_embedding_model(
    payload: EmbeddingModelCreate,
    current_user: User = Depends(require_current_active_user),
    embedding_model_service: EmbeddingModelService = Depends(get_embedding_model_service),
) -> EmbeddingModelResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    item = embedding_model_service.create_config(secured_payload)
    return EmbeddingModelResponse.model_validate(item)
```

`app/api/routes/document.py`

```python
@router.post("/import", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def import_document(
    payload: DocumentImportRequest,
    current_user: User = Depends(require_current_active_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    item = document_service.import_text(secured_payload)
    return DocumentResponse.model_validate(item)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    current_user: User = Depends(require_current_active_user),
    conversation_id: str | None = Query(default=None),
    document_service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    items = document_service.list_documents(
        team_id=current_user.team_id,
        conversation_id=conversation_id,
    )
    return [DocumentResponse.model_validate(item) for item in items]
```

`app/api/routes/favorite.py`

```python
@router.get("/answers", response_model=list[FavoriteAnswerResponse])
def list_favorite_answers(
    current_user: User = Depends(require_current_active_user),
    limit: int = Query(default=20, ge=1, le=200),
    favorite_service: FavoriteService = Depends(get_favorite_service),
) -> list[FavoriteAnswerResponse]:
    items = favorite_service.list_answers(
        team_id=current_user.team_id,
        user_id=current_user.user_id,
        limit=limit,
    )
    return [FavoriteAnswerResponse.model_validate(item) for item in items]
```

`app/api/routes/space.py`

```python
@router.get("", response_model=list[SpaceResponse])
def list_spaces(
    current_user: User = Depends(require_current_active_user),
    limit: int = Query(default=100, ge=1, le=200),
    space_service: SpaceService = Depends(get_space_service),
) -> list[SpaceResponse]:
    items = space_service.list(
        team_id=current_user.team_id,
        user_id=current_user.user_id,
        limit=limit,
    )
    return [SpaceResponse.model_validate(item) for item in items]


@router.delete("/{space_id}", response_model=SpaceResponse)
def delete_space(
    space_id: str,
    current_user: User = Depends(require_current_active_user),
    space_service: SpaceService = Depends(get_space_service),
) -> SpaceResponse:
    item = space_service.delete(
        space_id=space_id,
        team_id=current_user.team_id,
        user_id=current_user.user_id,
    )
    return SpaceResponse.model_validate(item)
```

`app/api/routes/library.py`

```python
@router.get("/documents", response_model=list[DocumentResponse])
def list_library_documents(
    current_user: User = Depends(require_current_active_user),
    space_id: str = Query(min_length=1, max_length=36),
    limit: int = Query(default=50, ge=1, le=200),
    document_service: DocumentService = Depends(get_document_service),
    space_service: SpaceService = Depends(get_space_service),
) -> list[DocumentResponse]:
    space_service.ensure_access(
        space_id=space_id,
        team_id=current_user.team_id,
        user_id=current_user.user_id,
    )
    items = document_service.list_documents(
        team_id=current_user.team_id,
        space_id=space_id,
        visibility="space",
        limit=limit,
    )
    return [DocumentResponse.model_validate(item) for item in items]
```

`app/api/routes/memory.py`

```python
@router.patch("/{memory_id}", response_model=MemoryCardResponse)
def update_memory_card(
    memory_id: str,
    payload: MemoryCardUpdate,
    current_user: User = Depends(require_current_active_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryCardResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    item = memory_service.update(memory_id=memory_id, payload=secured_payload)
    return MemoryCardResponse.model_validate(item)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory_card(
    memory_id: str,
    current_user: User = Depends(require_current_active_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> None:
    memory_service.delete(
        memory_id=memory_id,
        team_id=current_user.team_id,
        user_id=current_user.user_id,
    )
```

`app/api/routes/retrieval.py`

```python
@router.post("/index", response_model=RetrievalIndexResponse)
def index_chunks(
    payload: RetrievalIndexRequest,
    current_user: User = Depends(require_current_active_user),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalIndexResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    result = retrieval_service.index_chunks(secured_payload)
    return RetrievalIndexResponse.model_validate(result)


@router.post("/search", response_model=RetrievalSearchResponse)
def search_chunks(
    payload: RetrievalSearchRequest,
    current_user: User = Depends(require_current_active_user),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalSearchResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    result = retrieval_service.search(secured_payload)
    return RetrievalSearchResponse.model_validate(result)
```

`app/api/routes/conclusion.py`

```python
@router.post("", response_model=ConclusionResponse, status_code=status.HTTP_201_CREATED)
def create_conclusion(
    payload: ConclusionCreate,
    current_user: User = Depends(require_current_active_user),
    conclusion_service: ConclusionService = Depends(get_conclusion_service),
) -> ConclusionResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    item = conclusion_service.create(secured_payload)
    return ConclusionResponse.model_validate(item)


@router.post("/{conclusion_id}/confirm", response_model=ConclusionResponse)
def confirm_conclusion(
    conclusion_id: str,
    payload: ConclusionConfirm,
    current_user: User = Depends(require_current_active_user),
    conclusion_service: ConclusionService = Depends(get_conclusion_service),
) -> ConclusionResponse:
    secured_payload = payload.model_copy(
        update={"team_id": current_user.team_id, "user_id": current_user.user_id}
    )
    item = conclusion_service.confirm(conclusion_id=conclusion_id, payload=secured_payload)
    return ConclusionResponse.model_validate(item)
```

Update the corresponding test files so setup uses `register_workspace_user(...)` and authenticated cookies rather than `/teams` + `/users` bootstrap.

- [ ] **Step 4: Run the route cluster tests to verify they pass**

Run:

```powershell
pytest tests/test_authenticated_routes.py tests/test_document.py tests/test_retrieval.py tests/test_spaces_and_library.py tests/test_favorites_and_conclusions.py tests/test_llm_model.py tests/test_embedding_model.py -v
```

Expected: PASS with anonymous `401` smoke coverage and all existing success-path tests still green under authenticated sessions.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_authenticated_routes.py app/api/routes/document.py app/api/routes/retrieval.py app/api/routes/space.py app/api/routes/library.py app/api/routes/memory.py app/api/routes/favorite.py app/api/routes/conclusion.py app/api/routes/llm_model.py app/api/routes/embedding_model.py tests/test_document.py tests/test_retrieval.py tests/test_spaces_and_library.py tests/test_favorites_and_conclusions.py tests/test_llm_model.py tests/test_embedding_model.py
git commit -m "feat: protect remaining workspace routes"
```

### Task 8: Replace Workspace Bootstrap UI with Login/Register Session Flow

**Files:**
- Modify: `app/web/index.html`
- Modify: `app/web/styles.css`
- Modify: `app/web/app.js`
- Modify: `tests/test_web_assets.py`

- [ ] **Step 1: Write the failing frontend asset tests**

```python
def test_auth_modal_uses_login_register_language(client) -> None:
    html = _get_web_index(client)

    assert 'id="authModeLoginBtn"' in html
    assert 'id="authModeRegisterBtn"' in html
    assert 'for="passwordInput">密码<' in html
    assert 'for="confirmPasswordInput">确认密码<' in html
    assert 'id="logoutBtn"' in html
    assert "登录 / 注册" in html
    assert "工作台 ID" not in html


def test_frontend_bootstraps_from_auth_me_and_refresh(client) -> None:
    script = _get_web_app_script(client)

    assert '"/auth/me"' in script
    assert '"/auth/login"' in script
    assert '"/auth/register"' in script
    assert '"/auth/refresh"' in script
    assert '"/auth/logout"' in script
    assert "ensureTeam(" not in script
    assert "ensureUser(" not in script
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest tests/test_web_assets.py -v
```

Expected: FAIL because the HTML and JS still use the workspace bootstrap modal and `ensureTeam` / `ensureUser`.

- [ ] **Step 3: Write the minimal frontend auth implementation**

`app/web/index.html`

```html
<div id="authModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="authTitle">
  <div class="modal-card">
    <h2 id="authTitle">登录 / 注册</h2>
    <p class="modal-tip">登录后再进入你的个人工作台。资料、会话和偏好会跟随当前账号。</p>

    <div class="auth-mode-tabs">
      <button id="authModeLoginBtn" class="ghost-btn compact-btn" type="button">登录</button>
      <button id="authModeRegisterBtn" class="ghost-btn compact-btn" type="button">注册</button>
    </div>

    <div class="field">
      <label for="accountIdInput">账号 ID</label>
      <input id="accountIdInput" type="text" placeholder="例如：hibirdw" />
    </div>
    <div class="field">
      <label for="accountNameInput">显示名称</label>
      <input id="accountNameInput" type="text" placeholder="注册时填写，登录时可留空" />
    </div>
    <div class="field">
      <label for="passwordInput">密码</label>
      <input id="passwordInput" type="password" placeholder="至少 8 位" />
    </div>
    <div id="confirmPasswordField" class="field hidden">
      <label for="confirmPasswordInput">确认密码</label>
      <input id="confirmPasswordInput" type="password" placeholder="再次输入密码" />
    </div>

    <div class="modal-actions">
      <button id="cancelAuthBtn" class="ghost-btn compact-btn" type="button">取消</button>
      <button id="saveAuthBtn" class="primary-btn compact-primary-btn" type="button">登录</button>
    </div>
  </div>
</div>
```

Add logout affordance in the settings modal:

```html
<button id="logoutBtn" class="ghost-btn compact-btn" type="button">退出登录</button>
```

`app/web/app.js`

```javascript
const state = {
  teamId: "",
  teamName: "",
  userId: "",
  displayName: "",
  conversationId: "",
  selectedModel: DEFAULT_MODEL_ID,
  selectedEmbedding: DEFAULT_EMBEDDING_ID,
  authMode: "login",
  authChecked: false,
  modelConfigs: [],
  embeddingConfigs: [],
  conversations: [],
  history: [],
  documents: [],
  favoriteItems: [],
  favoriteWorkspaceAssets: createEmptyFavoriteWorkspaceAssetState(),
  selectedDocumentIds: [],
  chatMode: CHAT_MODE_CHAT,
  workspaceView: WORKSPACE_VIEW_CHAT,
  sending: false,
  importing: false,
  dragCounter: 0,
  messageCaptures: createEmptyMessageCaptureState(),
  pendingCaptureActions: {},
  messageCaptureRequestSeq: 0,
  favoriteWorkspaceRequestSeq: 0,
};

let refreshPromise = null;
```

Initialize from `/auth/me` instead of `localStorage` identity:

```javascript
document.addEventListener("DOMContentLoaded", async () => {
  bindElements();
  hydrateState();
  bindEvents();
  updateIdentityCard();
  initModelOptions();
  initEmbeddingOptions();
  renderAttachmentStrip();
  syncSendButtonState();
  refreshWorkspaceUi();

  await bootstrapAuthSession();
});

async function bootstrapAuthSession() {
  try {
    await loadCurrentSession();
    await loadAllData();
  } catch (error) {
    clearAuthenticatedState();
    openAuthModal();
  } finally {
    state.authChecked = true;
    refreshWorkspaceUi();
  }
}

async function loadCurrentSession() {
  const session = await apiRequest("/auth/me", { skipAuthRefresh: true });
  applyAuthenticatedSession(session);
}

function applyAuthenticatedSession(session) {
  state.teamId = session.team_id;
  state.teamName = session.team_name;
  state.userId = session.user_id;
  state.displayName = session.display_name;
  updateIdentityCard();
}

function clearAuthenticatedState() {
  state.teamId = "";
  state.teamName = "";
  state.userId = "";
  state.displayName = "";
  state.conversationId = "";
  state.selectedDocumentIds = [];
  clearConversation();
  updateIdentityCard();
}
```

Add login/register/logout handlers and refresh-once retry:

```javascript
async function handleSaveAuth() {
  const userId = els.accountIdInput?.value.trim() || "";
  const displayName = (els.accountNameInput?.value.trim() || userId).slice(0, 64);
  const password = els.passwordInput?.value || "";
  const confirmPassword = els.confirmPasswordInput?.value || "";

  if (!userId || !password) {
    showToast("请输入账号和密码", true);
    return;
  }

  setButtonLoading(els.saveAuthBtn, true, state.authMode === "register" ? "注册中..." : "登录中...");
  try {
    const path = state.authMode === "register" ? "/auth/register" : "/auth/login";
    const body =
      state.authMode === "register"
        ? { user_id: userId, display_name: displayName, password, confirm_password: confirmPassword }
        : { user_id: userId, password };

    const session = await apiRequest(path, { method: "POST", body, skipAuthRefresh: true });
    applyAuthenticatedSession(session);
    closeAuthModal();
    await loadAllData();
    showToast(state.authMode === "register" ? `注册成功：${session.display_name}` : `欢迎回来：${session.display_name}`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setButtonLoading(els.saveAuthBtn, false, state.authMode === "register" ? "注册" : "登录");
  }
}

async function handleLogout() {
  try {
    await apiRequest("/auth/logout", { method: "POST", skipAuthRefresh: true });
  } finally {
    clearAuthenticatedState();
    openAuthModal();
  }
}

async function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = apiRequest("/auth/refresh", {
      method: "POST",
      skipAuthRefresh: true,
    })
      .then((session) => {
        applyAuthenticatedSession(session);
        return true;
      })
      .catch(() => {
        clearAuthenticatedState();
        openAuthModal();
        return false;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function apiRequest(path, options = {}) {
  const useFormData = options.formData instanceof FormData;
  const requestOptions = {
    method: options.method || "GET",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(!useFormData && options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    body: useFormData ? options.formData : (options.body ? JSON.stringify(options.body) : undefined),
  };

  const response = await fetch(`${API_PREFIX}${path}`, requestOptions);
  if (response.status === 401 && !options.skipAuthRefresh) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return apiRequest(path, { ...options, skipAuthRefresh: true });
    }
  }

  const text = await response.text();
  let data;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : response.statusText;
    throw new Error(String(detail || `请求失败：${response.status}`));
  }
  return data;
}
```

`app/web/styles.css`

```css
.auth-mode-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.auth-mode-tabs .active {
  background: rgba(13, 127, 112, 0.12);
  border-color: rgba(13, 127, 112, 0.22);
  color: var(--accent-strong);
}

#confirmPasswordField.hidden {
  display: none;
}
```

Update `tests/test_web_assets.py` to remove the old assertions that require `ensureTeam(...)`, `ensureUser(...)`, and workspace-bootstrap wording.

- [ ] **Step 4: Run frontend asset tests to verify they pass**

Run:

```powershell
pytest tests/test_web_assets.py -v
```

Expected: PASS with new auth modal copy, new `/auth/*` client flow, and no leftover `ensureTeam` / `ensureUser` assertions.

- [ ] **Step 5: Commit**

```powershell
git add app/web/index.html app/web/styles.css app/web/app.js tests/test_web_assets.py
git commit -m "feat: replace workspace bootstrap with auth session flow"
```

### Task 9: Full Verification

**Files:**
- None. Verification only.

- [ ] **Step 1: Run the auth-focused backend suite**

Run:

```powershell
pytest tests/test_config.py tests/test_migrations.py tests/test_security.py tests/test_auth.py -v
```

Expected: PASS for config, migration, token helpers, register/login/me, refresh rotation, and password change.

- [ ] **Step 2: Run the protected-route regression suite**

Run:

```powershell
pytest tests/test_authenticated_routes.py tests/test_conversation.py tests/test_chat.py tests/test_document.py tests/test_retrieval.py tests/test_spaces_and_library.py tests/test_favorites_and_conclusions.py tests/test_llm_model.py tests/test_embedding_model.py -v
```

Expected: PASS with anonymous `401` checks and all authenticated business flows green.

- [ ] **Step 3: Run the frontend asset regression suite**

Run:

```powershell
pytest tests/test_web_assets.py -v
```

Expected: PASS for updated login/register markup and auth bootstrap JS assertions.

- [ ] **Step 4: Run the full test suite**

Run:

```powershell
pytest -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Perform manual browser smoke verification**

Run:

```powershell
uvicorn app.main:app --reload
```

Then verify manually in a browser:

- Register a new account and confirm the app lands in the workspace
- Refresh the page and confirm `/auth/me` restores the session
- Delete the access cookie in DevTools, trigger a request, and confirm refresh recovers the session
- Log out and confirm protected actions redirect back to login
- Change password, confirm the current session is cleared, old password fails, and new password works

- [ ] **Step 6: Final commit**

```powershell
git status --short
git add -A
git commit -m "feat: complete standard auth loop"
```

## Self-Review Checklist

- Spec coverage:
  - Config, schema, migration, auth routes, route protection, frontend bootstrap, refresh, logout, and password change are all mapped to explicit tasks.
  - Admin token flow is intentionally excluded.
- Placeholder scan:
  - No unresolved placeholders or shortcut phrases remain.
  - Every task names exact files and test commands.
- Type consistency:
  - `auth_access_cookie_name`, `auth_refresh_cookie_name`, `password_updated_at`, `require_current_active_user`, and `/api/v1/auth/*` naming stays consistent across tasks.
