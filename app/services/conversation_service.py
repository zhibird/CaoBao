from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.chat_history import ChatHistory
from app.models.chunk_embedding import ChunkEmbedding
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.user_service import UserService


class ConversationService:
    def __init__(self, db: Session, user_service: UserService) -> None:
        self.db = db
        self.user_service = user_service

    def create(self, *, team_id: str, user_id: str, title: str | None = None) -> Conversation:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)

        conversation = Conversation(
            conversation_id=str(uuid4()),
            team_id=team_id,
            user_id=user_id,
            title=title.strip() if title else "新会话",
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list(
        self,
        *,
        team_id: str,
        user_id: str,
        limit: int = 50,
    ) -> list[Conversation]:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)

        if limit < 1 or limit > 200:
            raise DomainValidationError("limit must be between 1 and 200.")

        stmt = (
            select(Conversation)
            .where(
                Conversation.team_id == team_id,
                Conversation.user_id == user_id,
                Conversation.status == "active",
            )
            .order_by(Conversation.created_at.desc(), Conversation.conversation_id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def ensure_access(self, *, conversation_id: str, team_id: str, user_id: str) -> Conversation:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)

        conversation = self.db.get(Conversation, conversation_id)
        if conversation is None or conversation.status != "active":
            raise EntityNotFoundError(f"Conversation '{conversation_id}' not found.")

        if conversation.team_id != team_id or conversation.user_id != user_id:
            raise DomainValidationError("Conversation does not belong to the provided team/user.")

        return conversation

    def rename(self, *, conversation_id: str, team_id: str, user_id: str, title: str) -> Conversation:
        normalized_title = title.strip()
        if not normalized_title:
            raise DomainValidationError("title cannot be empty.")

        if len(normalized_title) > 255:
            raise DomainValidationError("title length must be less than or equal to 255.")

        conversation = self.ensure_access(
            conversation_id=conversation_id,
            team_id=team_id,
            user_id=user_id,
        )
        conversation.title = normalized_title
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def delete(self, *, conversation_id: str, team_id: str, user_id: str) -> None:
        self.ensure_access(conversation_id=conversation_id, team_id=team_id, user_id=user_id)

        document_ids_stmt = select(Document.document_id).where(
            Document.team_id == team_id,
            Document.conversation_id == conversation_id,
        )
        document_ids = list(self.db.scalars(document_ids_stmt).all())

        if document_ids:
            self.db.execute(
                delete(ChunkEmbedding).where(
                    ChunkEmbedding.team_id == team_id,
                    ChunkEmbedding.document_id.in_(document_ids),
                )
            )
            self.db.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.team_id == team_id,
                    DocumentChunk.document_id.in_(document_ids),
                )
            )
            self.db.execute(
                delete(Document).where(
                    Document.team_id == team_id,
                    Document.conversation_id == conversation_id,
                )
            )

        self.db.execute(
            delete(ChatHistory).where(
                ChatHistory.team_id == team_id,
                ChatHistory.user_id == user_id,
                ChatHistory.conversation_id == conversation_id,
            )
        )

        self.db.execute(
            delete(Conversation).where(
                Conversation.conversation_id == conversation_id,
                Conversation.team_id == team_id,
                Conversation.user_id == user_id,
            )
        )
        self.db.commit()
