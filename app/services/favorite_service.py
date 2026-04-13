from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.chat_history import ChatHistory
from app.schemas.favorite import (
    FavoriteCreate,
    FavoritePromoteToConclusionRequest,
    FavoritePromoteToMemoryRequest,
    FavoriteUpdate,
)
from app.schemas.memory import MemoryCardCreate
from app.services.space_service import SpaceService
from app.services.user_service import UserService


class FavoriteService:
    def __init__(
        self,
        db: Session,
        user_service: UserService,
        space_service: SpaceService,
    ) -> None:
        self.db = db
        self.user_service = user_service
        self.space_service = space_service

    def create(self, payload: FavoriteCreate):
        self.space_service.ensure_access(
            space_id=payload.space_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )
        history = self._load_chat_history_for_favorite(
            message_id=payload.message_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )

        favorite_model = self._favorite_model()
        now = datetime.now(timezone.utc)
        title = (payload.title or "").strip() or self._build_default_title(history)
        tags_json = self._normalize_tags_json(payload.tags)
        sources_json = self._extract_sources_json(history.response_payload_json)
        favorite = favorite_model(
            favorite_id=str(uuid4()),
            team_id=payload.team_id,
            space_id=payload.space_id,
            user_id=payload.user_id,
            conversation_id=history.conversation_id,
            message_id=history.message_id,
            title=title,
            question_text=history.request_text,
            answer_text=history.response_text,
            sources_json=sources_json,
            note=(payload.note or "").strip() or None,
            tags_json=tags_json,
            is_promoted=False,
            created_at=now,
            updated_at=now,
        )
        self.db.add(favorite)
        self.db.commit()
        self.db.refresh(favorite)
        return favorite

    def list(
        self,
        *,
        team_id: str,
        user_id: str,
        space_id: str,
        limit: int = 50,
    ) -> list:
        self.space_service.ensure_access(space_id=space_id, team_id=team_id, user_id=user_id)
        if limit < 1 or limit > 200:
            raise DomainValidationError("limit must be between 1 and 200.")

        favorite_model = self._favorite_model()
        stmt = (
            select(favorite_model)
            .where(
                favorite_model.team_id == team_id,
                favorite_model.user_id == user_id,
                favorite_model.space_id == space_id,
            )
            .order_by(favorite_model.created_at.desc(), favorite_model.favorite_id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def update(self, *, favorite_id: str, payload: FavoriteUpdate):
        favorite = self.ensure_access(
            favorite_id=favorite_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )
        if payload.title is not None:
            title = payload.title.strip()
            if not title:
                raise DomainValidationError("title cannot be empty.")
            favorite.title = title
        if payload.note is not None:
            favorite.note = payload.note.strip() or None
        if payload.tags is not None:
            favorite.tags_json = self._normalize_tags_json(payload.tags)
        favorite.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(favorite)
        return favorite

    def delete(self, *, favorite_id: str, team_id: str, user_id: str) -> None:
        favorite = self.ensure_access(favorite_id=favorite_id, team_id=team_id, user_id=user_id)
        self.db.delete(favorite)
        self.db.commit()

    def promote_to_memory(
        self,
        *,
        favorite_id: str,
        payload: FavoritePromoteToMemoryRequest,
        memory_service,
    ) -> dict[str, object]:
        favorite = self.ensure_access(
            favorite_id=favorite_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )
        target_space_id = payload.space_id or favorite.space_id
        self.space_service.ensure_access(
            space_id=target_space_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )

        memory = memory_service.create(
            MemoryCardCreate(
                team_id=payload.team_id,
                user_id=payload.user_id,
                space_id=target_space_id,
                category=payload.category,
                title=(payload.title or "").strip() or favorite.title,
                content=favorite.answer_text,
                summary=payload.summary,
                weight=payload.weight,
                confidence=payload.confidence,
                status=payload.status,
                source_message_id=favorite.message_id,
                expires_at=payload.expires_at,
            )
        )
        favorite.is_promoted = True
        favorite.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(favorite)
        return {
            "favorite": favorite,
            "memory_id": getattr(memory, "memory_id", None),
        }

    def promote_to_conclusion(
        self,
        *,
        favorite_id: str,
        payload: FavoritePromoteToConclusionRequest,
        conclusion_service,
    ) -> dict[str, object]:
        favorite = self.ensure_access(
            favorite_id=favorite_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )
        target_space_id = payload.space_id or favorite.space_id
        self.space_service.ensure_access(
            space_id=target_space_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )

        create_from_favorite = getattr(conclusion_service, "create_from_favorite", None)
        if not callable(create_from_favorite):
            raise DomainValidationError("Conclusion service does not support favorite promotion.")

        conclusion = create_from_favorite(
            favorite=favorite,
            team_id=payload.team_id,
            user_id=payload.user_id,
            space_id=target_space_id,
            title=payload.title,
            topic=payload.topic,
            summary=payload.summary,
            confidence=payload.confidence,
            status=payload.status,
        )
        favorite.is_promoted = True
        favorite.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(favorite)
        return {
            "favorite": favorite,
            "conclusion_id": getattr(conclusion, "conclusion_id", None),
        }

    def ensure_access(self, *, favorite_id: str, team_id: str, user_id: str):
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)
        favorite_model = self._favorite_model()
        favorite = self.db.get(favorite_model, favorite_id)
        if favorite is None:
            raise EntityNotFoundError(f"Favorite '{favorite_id}' not found.")
        if favorite.team_id != team_id or favorite.user_id != user_id:
            raise EntityNotFoundError(f"Favorite '{favorite_id}' not found.")
        self.space_service.ensure_access(
            space_id=favorite.space_id,
            team_id=team_id,
            user_id=user_id,
        )
        return favorite

    def _load_chat_history_for_favorite(
        self,
        *,
        message_id: str,
        team_id: str,
        user_id: str,
    ) -> ChatHistory:
        history = self.db.get(ChatHistory, message_id)
        if history is None:
            raise EntityNotFoundError(f"Message '{message_id}' not found.")
        if history.team_id != team_id or history.user_id != user_id:
            raise EntityNotFoundError(f"Message '{message_id}' not found.")
        if history.channel not in {"ask", "echo"}:
            raise DomainValidationError("Only ask/echo messages can be favorited.")
        return history

    def _build_default_title(self, history: ChatHistory) -> str:
        question = (history.request_text or "").strip()
        if not question:
            return "Favorite Answer"
        return question[:128]

    def _extract_sources_json(self, raw_response_payload_json: str) -> str | None:
        try:
            payload = json.loads(raw_response_payload_json or "{}")
        except (TypeError, json.JSONDecodeError):
            return None
        sources = payload.get("sources") if isinstance(payload, dict) else None
        if not isinstance(sources, list):
            return None
        return json.dumps(sources, ensure_ascii=False, separators=(",", ":"))

    def _normalize_tags_json(self, tags: list[str] | None) -> str | None:
        if not tags:
            return None
        normalized: list[str] = []
        for item in tags:
            value = str(item).strip()
            if value and value not in normalized:
                normalized.append(value)
        if not normalized:
            return None
        return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))

    def _favorite_model(self):
        from app.models.answer_favorite import AnswerFavorite

        return AnswerFavorite
