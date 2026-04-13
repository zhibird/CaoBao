from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import DomainValidationError, EntityConflictError, EntityNotFoundError
from app.core.security import create_access_token, generate_refresh_token, hash_password, hash_refresh_token, verify_password
from app.models.auth_refresh_session import AuthRefreshSession
from app.models.team import Team
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


@dataclass(slots=True)
class AuthResult:
    user: User
    team_name: str
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def register(
        self,
        payload: RegisterRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResult:
        self._validate_password_confirmation(payload.password, payload.confirm_password)
        if self.db.get(User, payload.user_id) is not None:
            raise EntityConflictError(f"User '{payload.user_id}' already exists.")
        if self.db.get(Team, payload.user_id) is not None:
            raise EntityConflictError(f"Team '{payload.user_id}' already exists.")

        now = datetime.now(timezone.utc)
        password_hash = hash_password(payload.password)
        team = Team(team_id=payload.user_id, name=payload.display_name, description=None)
        user = User(
            user_id=payload.user_id,
            team_id=payload.user_id,
            display_name=payload.display_name,
            role="member",
            password_hash=password_hash,
            is_active=True,
            password_updated_at=now,
        )
        self.db.add(team)
        self.db.add(user)
        self.db.flush()
        return self._issue_session(user, team_name=team.name, user_agent=user_agent, ip_address=ip_address)

    def login(
        self,
        payload: LoginRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResult:
        user = self.db.get(User, payload.user_id)
        if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
            raise DomainValidationError("Invalid credentials.")

        if user.password_updated_at is None:
            user.password_updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()

        team = self.db.get(Team, user.team_id)
        if team is None:
            raise DomainValidationError("Invalid credentials.")

        return self._issue_session(user, team_name=team.name, user_agent=user_agent, ip_address=ip_address)

    def get_current_user_from_request(self, request: Request) -> User:
        raw_token = request.cookies.get(self.settings.auth_access_cookie_name)
        if not raw_token:
            raise DomainValidationError("Authentication required.")

        try:
            payload = jwt.decode(
                raw_token,
                self.settings.auth_jwt_secret,
                algorithms=[self.settings.auth_jwt_algorithm],
            )
        except jwt.PyJWTError as exc:
            raise DomainValidationError("Authentication required.") from exc

        user_id = str(payload.get("sub") or "")
        if not user_id:
            raise DomainValidationError("Authentication required.")

        user = self.db.get(User, user_id)
        if user is None or not user.password_hash:
            raise DomainValidationError("Authentication required.")

        if int(payload.get("pwd_ts", 0)) != self._password_timestamp(user.password_updated_at):
            raise DomainValidationError("Authentication required.")

        return user

    def get_team_name(self, team_id: str) -> str:
        team = self.db.get(Team, team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{team_id}' not found.")
        return team.name

    def refresh(
        self,
        *,
        refresh_token: str | None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResult:
        refresh_session = self._get_valid_refresh_session(refresh_token)
        user = self.db.get(User, refresh_session.user_id)
        if user is None or not user.is_active or not user.password_hash:
            raise DomainValidationError("Authentication required.")

        team = self.db.get(Team, user.team_id)
        if team is None:
            raise DomainValidationError("Authentication required.")

        replacement = self._issue_session(
            user,
            team_name=team.name,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        refresh_session.rotated_at = datetime.now(timezone.utc)
        newest_session = self.db.scalars(
            select(AuthRefreshSession).where(
                AuthRefreshSession.refresh_token_hash == hash_refresh_token(replacement.refresh_token)
            )
        ).first()
        if newest_session is not None:
            refresh_session.replaced_by_session_id = newest_session.session_id
        self.db.add(refresh_session)
        self.db.commit()
        return replacement

    def revoke_refresh_session(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return

        token_hash = hash_refresh_token(refresh_token)
        refresh_session = self.db.scalars(
            select(AuthRefreshSession).where(AuthRefreshSession.refresh_token_hash == token_hash)
        ).first()
        if refresh_session is None or refresh_session.revoked_at is not None:
            return

        refresh_session.revoked_at = datetime.now(timezone.utc)
        self.db.add(refresh_session)
        self.db.commit()

    def revoke_all_refresh_sessions_for_user(self, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        refresh_sessions = self.db.scalars(
            select(AuthRefreshSession).where(
                AuthRefreshSession.user_id == user_id,
                AuthRefreshSession.revoked_at.is_(None),
            )
        ).all()
        for refresh_session in refresh_sessions:
            refresh_session.revoked_at = now
            self.db.add(refresh_session)
        self.db.commit()

    def change_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
        confirm_new_password: str,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise DomainValidationError("Invalid credentials.")

        self._validate_password_confirmation(new_password, confirm_new_password)
        user.password_hash = hash_password(new_password)
        user.password_updated_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.commit()
        self.revoke_all_refresh_sessions_for_user(user.user_id)

    def write_auth_cookies(self, response: Response, *, access_token: str, refresh_token: str) -> None:
        cookie_kwargs = dict(
            httponly=True,
            secure=self.settings.auth_cookie_secure,
            samesite=self.settings.auth_cookie_samesite,
            domain=self.settings.auth_cookie_domain,
            path="/",
        )
        response.set_cookie(
            self.settings.auth_access_cookie_name,
            access_token,
            max_age=self.settings.auth_access_token_ttl_minutes * 60,
            **cookie_kwargs,
        )
        response.set_cookie(
            self.settings.auth_refresh_cookie_name,
            refresh_token,
            max_age=self.settings.auth_refresh_token_ttl_days * 24 * 60 * 60,
            **cookie_kwargs,
        )

    def clear_auth_cookies(self, response: Response) -> None:
        response.delete_cookie(
            self.settings.auth_access_cookie_name,
            path="/",
            domain=self.settings.auth_cookie_domain,
        )
        response.delete_cookie(
            self.settings.auth_refresh_cookie_name,
            path="/",
            domain=self.settings.auth_cookie_domain,
        )

    def _issue_session(
        self,
        user: User,
        *,
        team_name: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthResult:
        if user.password_updated_at is None:
            user.password_updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()

        password_timestamp = self._password_timestamp(user.password_updated_at)
        access_token = create_access_token(
            subject=user.user_id,
            team_id=user.team_id,
            role=user.role,
            password_timestamp=password_timestamp,
            settings=self.settings,
        )
        refresh_token = generate_refresh_token()
        now = datetime.now(timezone.utc)
        refresh_session = AuthRefreshSession(
            session_id=uuid4().hex,
            user_id=user.user_id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            issued_at=now,
            expires_at=now + timedelta(days=self.settings.auth_refresh_token_ttl_days),
            rotated_at=None,
            revoked_at=None,
            replaced_by_session_id=None,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(refresh_session)
        self.db.commit()
        self.db.refresh(user)
        return AuthResult(
            user=user,
            team_name=team_name,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @staticmethod
    def _validate_password_confirmation(password: str, confirm_password: str) -> None:
        if password != confirm_password:
            raise DomainValidationError("Passwords do not match.")

    @staticmethod
    def _normalize_datetime(raw_value: datetime) -> datetime:
        if raw_value.tzinfo is None:
            return raw_value.replace(tzinfo=timezone.utc)
        return raw_value.astimezone(timezone.utc)

    def _get_valid_refresh_session(self, refresh_token: str | None) -> AuthRefreshSession:
        if not refresh_token:
            raise DomainValidationError("Authentication required.")

        token_hash = hash_refresh_token(refresh_token)
        refresh_session = self.db.scalars(
            select(AuthRefreshSession).where(AuthRefreshSession.refresh_token_hash == token_hash)
        ).first()
        if refresh_session is None or refresh_session.revoked_at is not None or refresh_session.rotated_at is not None:
            raise DomainValidationError("Authentication required.")
        if self._normalize_datetime(refresh_session.expires_at) <= datetime.now(timezone.utc):
            raise DomainValidationError("Authentication required.")
        return refresh_session

    @staticmethod
    def _password_timestamp(password_updated_at: datetime | None) -> int:
        if password_updated_at is None:
            return 0
        normalized = AuthService._normalize_datetime(password_updated_at)
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        delta = normalized - epoch
        return ((delta.days * 24 * 60 * 60) + delta.seconds) * 1_000_000 + delta.microseconds
