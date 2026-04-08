from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, EntityConflictError, EntityNotFoundError
from app.models.team import Team
from app.models.user import User
from app.schemas.user import UserCreate, UserEnsure


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user(self, payload: UserCreate) -> User:
        team = self.db.get(Team, payload.team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{payload.team_id}' does not exist.")

        existing = self.db.get(User, payload.user_id)
        if existing is not None:
            raise EntityConflictError(f"User '{payload.user_id}' already exists.")

        user = User(
            user_id=payload.user_id,
            team_id=payload.team_id,
            display_name=payload.display_name,
            role=payload.role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def ensure_user(self, *, user_id: str, payload: UserEnsure) -> tuple[User, bool]:
        team = self.db.get(Team, payload.team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{payload.team_id}' does not exist.")

        existing = self.db.get(User, user_id)
        if existing is None:
            user = User(
                user_id=user_id,
                team_id=payload.team_id,
                display_name=payload.display_name,
                role="member",
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user, True

        if existing.team_id != payload.team_id:
            raise EntityConflictError(
                f"User '{user_id}' already exists in team '{existing.team_id}'."
            )

        if existing.display_name != payload.display_name:
            existing.display_name = payload.display_name
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)

        return existing, False

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def list_users(self, team_id: str | None = None) -> list[User]:
        stmt = select(User).order_by(User.created_at.desc())
        if team_id is not None:
            stmt = stmt.where(User.team_id == team_id)
        return list(self.db.scalars(stmt).all())

    def ensure_user_in_team(self, user_id: str, team_id: str) -> User:
        user = self.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundError(f"User '{user_id}' does not exist.")

        if user.team_id != team_id:
            raise DomainValidationError(
                f"User '{user_id}' belongs to team '{user.team_id}', not '{team_id}'."
            )

        return user
