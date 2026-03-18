from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.chat_history import ChatHistory
from app.models.conversation import Conversation
from app.models.team import Team


class ChatHistoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_message(
        self,
        *,
        team_id: str,
        user_id: str,
        conversation_id: str | None,
        channel: str,
        request_text: str,
        response_text: str,
        request_payload: dict[str, object],
        response_payload: dict[str, object],
    ) -> ChatHistory:
        normalized_channel = channel.strip().lower()
        if normalized_channel not in {"echo", "ask", "action"}:
            raise DomainValidationError("channel must be one of: echo, ask, action.")

        if conversation_id is not None:
            conversation = self.db.get(Conversation, conversation_id)
            if conversation is None:
                raise EntityNotFoundError(f"Conversation '{conversation_id}' does not exist.")
            if conversation.team_id != team_id or conversation.user_id != user_id:
                raise DomainValidationError(
                    f"Conversation '{conversation_id}' does not belong to team/user."
                )

        message = ChatHistory(
            message_id=str(uuid4()),
            team_id=team_id,
            user_id=user_id,
            conversation_id=conversation_id,
            channel=normalized_channel,
            request_text=request_text,
            response_text=response_text,
            request_payload_json=json.dumps(request_payload, ensure_ascii=False, separators=(",", ":")),
            response_payload_json=json.dumps(response_payload, ensure_ascii=False, separators=(",", ":")),
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_history(
        self,
        *,
        team_id: str,
        user_id: str | None = None,
        conversation_id: str | None = None,
        limit: int = 20,
    ) -> list[ChatHistory]:
        self._ensure_team_exists(team_id)

        if limit < 1 or limit > 200:
            raise DomainValidationError("limit must be between 1 and 200.")

        stmt = select(ChatHistory).where(ChatHistory.team_id == team_id)
        if user_id is not None:
            stmt = stmt.where(ChatHistory.user_id == user_id)
        if conversation_id is not None:
            conversation = self.db.get(Conversation, conversation_id)
            if conversation is None:
                raise EntityNotFoundError(f"Conversation '{conversation_id}' does not exist.")
            if conversation.team_id != team_id:
                raise DomainValidationError(
                    f"Conversation '{conversation_id}' does not belong to team '{team_id}'."
                )
            if user_id is not None and conversation.user_id != user_id:
                raise DomainValidationError(
                    f"Conversation '{conversation_id}' does not belong to user '{user_id}'."
                )
            stmt = stmt.where(ChatHistory.conversation_id == conversation_id)

        stmt = stmt.order_by(ChatHistory.created_at.desc(), ChatHistory.message_id.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def _ensure_team_exists(self, team_id: str) -> None:
        team = self.db.get(Team, team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{team_id}' does not exist.")
