from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.project_space import ProjectSpace
from app.schemas.space import SpaceCreate, SpaceUpdate
from app.services.user_service import UserService


class SpaceService:
    def __init__(self, db: Session, user_service: UserService) -> None:
        self.db = db
        self.user_service = user_service

    def create(self, payload: SpaceCreate) -> ProjectSpace:
        self.user_service.ensure_user_in_team(user_id=payload.user_id, team_id=payload.team_id)

        space = ProjectSpace(
            space_id=str(uuid4()),
            team_id=payload.team_id,
            owner_user_id=payload.user_id,
            name=payload.name.strip(),
            description=(payload.description or "").strip() or None,
            status="active",
            is_default=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(space)
        self.db.commit()
        self.db.refresh(space)
        return space

    def ensure_default_space(self, *, team_id: str, user_id: str) -> ProjectSpace:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)

        stmt = (
            select(ProjectSpace)
            .where(
                ProjectSpace.team_id == team_id,
                ProjectSpace.owner_user_id == user_id,
                ProjectSpace.is_default.is_(True),
                ProjectSpace.status == "active",
            )
            .limit(1)
        )
        existing = self.db.scalar(stmt)
        if existing is not None:
            return existing

        space = ProjectSpace(
            space_id=str(uuid4()),
            team_id=team_id,
            owner_user_id=user_id,
            name="Default Space",
            description=None,
            status="active",
            is_default=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(space)
        self.db.commit()
        self.db.refresh(space)
        return space

    def list(self, *, team_id: str, user_id: str, limit: int = 100) -> list[ProjectSpace]:
        self.ensure_default_space(team_id=team_id, user_id=user_id)

        if limit < 1 or limit > 200:
            raise DomainValidationError("limit must be between 1 and 200.")

        stmt = (
            select(ProjectSpace)
            .where(
                ProjectSpace.team_id == team_id,
                ProjectSpace.owner_user_id == user_id,
                ProjectSpace.status != "deleted",
            )
            .order_by(
                ProjectSpace.is_default.desc(),
                ProjectSpace.updated_at.desc(),
                ProjectSpace.space_id.desc(),
            )
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def ensure_access(self, *, space_id: str, team_id: str, user_id: str) -> ProjectSpace:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)

        space = self.db.get(ProjectSpace, space_id)
        if space is None or space.status == "deleted":
            raise EntityNotFoundError(f"Space '{space_id}' not found.")
        if space.team_id != team_id or space.owner_user_id != user_id:
            raise EntityNotFoundError(f"Space '{space_id}' not found.")
        return space

    def update(self, *, space_id: str, payload: SpaceUpdate) -> ProjectSpace:
        space = self.ensure_access(space_id=space_id, team_id=payload.team_id, user_id=payload.user_id)

        if payload.name is not None:
            normalized_name = payload.name.strip()
            if not normalized_name:
                raise DomainValidationError("name cannot be empty.")
            space.name = normalized_name

        if payload.description is not None:
            space.description = payload.description.strip() or None

        if payload.status is not None:
            normalized_status = payload.status.strip().lower()
            if normalized_status not in {"active", "archived"}:
                raise DomainValidationError("status must be one of: active, archived.")
            if space.is_default and normalized_status != "active":
                raise DomainValidationError("Default space cannot be archived.")
            space.status = normalized_status

        space.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(space)
        return space

    def delete(self, *, space_id: str, team_id: str, user_id: str) -> ProjectSpace:
        space = self.ensure_access(space_id=space_id, team_id=team_id, user_id=user_id)
        if space.is_default:
            raise DomainValidationError("Default space cannot be deleted.")

        space.status = "deleted"
        space.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(space)
        return space
