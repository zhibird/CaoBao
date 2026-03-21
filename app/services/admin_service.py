from __future__ import annotations

from typing import Any

from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.chat_history import ChatHistory
from app.models.chunk_embedding import ChunkEmbedding
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.embedding_model_config import EmbeddingModelConfig
from app.models.llm_model_config import LLMModelConfig
from app.models.team import Team
from app.models.user import User
from app.schemas.admin import (
    AdminConversationItem,
    AdminDashboardResponse,
    AdminDocumentDetail,
    AdminDocumentItem,
    AdminTeamItem,
    AdminUserItem,
)


class AdminService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def authenticate(self, token: str | None) -> User:
        if not self.settings.dev_admin_enabled:
            raise DomainValidationError("Developer admin mode is disabled.")

        expected_token = self.settings.dev_admin_token.strip()
        if not expected_token:
            raise DomainValidationError("DEV_ADMIN_TOKEN is not configured.")

        if token is None or token.strip() != expected_token:
            raise DomainValidationError("Invalid developer admin token.")

        return self.ensure_admin_account()

    def ensure_admin_account(self) -> User:
        account_id = self.settings.dev_admin_account_id.strip()
        if not account_id:
            raise DomainValidationError("DEV_ADMIN_ACCOUNT_ID cannot be empty.")

        display_name = self.settings.dev_admin_display_name.strip() or "Developer Admin"
        description = "Developer-only admin team managed by configuration."

        team = self.db.get(Team, account_id)
        if team is None:
            team = Team(
                team_id=account_id,
                name=f"{display_name} Team",
                description=description,
            )
            self.db.add(team)

        user = self.db.get(User, account_id)
        if user is None:
            user = User(
                user_id=account_id,
                team_id=account_id,
                display_name=display_name,
                role="admin",
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user

        if user.team_id != account_id:
            raise DomainValidationError(
                "Configured developer admin user exists in a different team. "
                "Please fix DEV_ADMIN_ACCOUNT_ID or clean up the conflicting record."
            )

        changed = False
        if user.display_name != display_name:
            user.display_name = display_name
            changed = True
        if user.role != "admin":
            user.role = "admin"
            changed = True

        if changed:
            self.db.commit()
            self.db.refresh(user)

        return user

    def dashboard(self) -> AdminDashboardResponse:
        return AdminDashboardResponse(
            teams=self._count_table(Team.team_id),
            users=self._count_table(User.user_id),
            conversations=self._count_table(Conversation.conversation_id),
            documents=self._count_table(Document.document_id),
            messages=self._count_table(ChatHistory.message_id),
        )

    def list_teams(self, limit: int = 200) -> list[AdminTeamItem]:
        stmt = select(Team).order_by(Team.created_at.desc()).limit(limit)
        teams = list(self.db.scalars(stmt).all())
        if not teams:
            return []

        team_ids = [item.team_id for item in teams]
        user_count_map = self._count_map(
            select(User.team_id, func.count(User.user_id))
            .where(User.team_id.in_(team_ids))
            .group_by(User.team_id)
        )
        conversation_count_map = self._count_map(
            select(Conversation.team_id, func.count(Conversation.conversation_id))
            .where(Conversation.team_id.in_(team_ids))
            .group_by(Conversation.team_id)
        )
        document_count_map = self._count_map(
            select(Document.team_id, func.count(Document.document_id))
            .where(Document.team_id.in_(team_ids))
            .group_by(Document.team_id)
        )

        return [
            AdminTeamItem(
                team_id=item.team_id,
                name=item.name,
                description=item.description,
                created_at=item.created_at,
                user_count=user_count_map.get(item.team_id, 0),
                conversation_count=conversation_count_map.get(item.team_id, 0),
                document_count=document_count_map.get(item.team_id, 0),
            )
            for item in teams
        ]

    def delete_team(self, team_id: str) -> None:
        if team_id == self.settings.dev_admin_account_id:
            raise DomainValidationError("Cannot delete the configured developer admin team.")

        team = self.db.get(Team, team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{team_id}' not found.")

        document_ids_stmt = select(Document.document_id).where(Document.team_id == team_id)
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

        self.db.execute(delete(Document).where(Document.team_id == team_id))
        self.db.execute(delete(ChatHistory).where(ChatHistory.team_id == team_id))
        self.db.execute(delete(Conversation).where(Conversation.team_id == team_id))
        self.db.execute(delete(LLMModelConfig).where(LLMModelConfig.team_id == team_id))
        self.db.execute(delete(EmbeddingModelConfig).where(EmbeddingModelConfig.team_id == team_id))
        self.db.execute(delete(User).where(User.team_id == team_id))
        self.db.execute(delete(Team).where(Team.team_id == team_id))
        self.db.commit()

    def list_users(self, team_id: str | None = None, limit: int = 300) -> list[AdminUserItem]:
        stmt = select(User).order_by(User.created_at.desc())
        if team_id is not None:
            stmt = stmt.where(User.team_id == team_id)
        users = list(self.db.scalars(stmt.limit(limit)).all())
        if not users:
            return []

        user_ids = [item.user_id for item in users]
        conversation_stmt = (
            select(Conversation.user_id, func.count(Conversation.conversation_id))
            .where(Conversation.user_id.in_(user_ids))
            .group_by(Conversation.user_id)
        )
        if team_id is not None:
            conversation_stmt = conversation_stmt.where(Conversation.team_id == team_id)
        conversation_count_map = self._count_map(conversation_stmt)

        document_stmt = (
            select(Conversation.user_id, func.count(Document.document_id))
            .join(
                Document,
                and_(
                    Document.conversation_id == Conversation.conversation_id,
                    Document.team_id == Conversation.team_id,
                ),
            )
            .where(Conversation.user_id.in_(user_ids))
            .group_by(Conversation.user_id)
        )
        if team_id is not None:
            document_stmt = document_stmt.where(Conversation.team_id == team_id)
        document_count_map = self._count_map(document_stmt)

        return [
            AdminUserItem(
                user_id=item.user_id,
                team_id=item.team_id,
                display_name=item.display_name,
                role=item.role,
                created_at=item.created_at,
                conversation_count=conversation_count_map.get(item.user_id, 0),
                document_count=document_count_map.get(item.user_id, 0),
            )
            for item in users
        ]

    def update_user_role(self, *, user_id: str, role: str) -> AdminUserItem:
        user = self.db.get(User, user_id)
        if user is None:
            raise EntityNotFoundError(f"User '{user_id}' not found.")

        normalized_role = role.strip()
        if not normalized_role:
            raise DomainValidationError("role cannot be empty.")

        if user.user_id == self.settings.dev_admin_account_id and normalized_role != "admin":
            raise DomainValidationError("Cannot downgrade the configured developer admin user.")

        user.role = normalized_role
        self.db.commit()
        self.db.refresh(user)

        conversation_count = self._count_by_user(user_id=user.user_id, team_id=user.team_id)
        document_count = self._count_documents_by_user(user_id=user.user_id, team_id=user.team_id)
        return AdminUserItem(
            user_id=user.user_id,
            team_id=user.team_id,
            display_name=user.display_name,
            role=user.role,
            created_at=user.created_at,
            conversation_count=conversation_count,
            document_count=document_count,
        )

    def delete_user(self, user_id: str) -> None:
        if user_id == self.settings.dev_admin_account_id:
            raise DomainValidationError("Cannot delete the configured developer admin user.")

        user = self.db.get(User, user_id)
        if user is None:
            raise EntityNotFoundError(f"User '{user_id}' not found.")

        conversation_ids_stmt = select(Conversation.conversation_id).where(
            Conversation.team_id == user.team_id,
            Conversation.user_id == user.user_id,
        )
        conversation_ids = list(self.db.scalars(conversation_ids_stmt).all())
        if conversation_ids:
            document_ids_stmt = select(Document.document_id).where(
                Document.team_id == user.team_id,
                Document.conversation_id.in_(conversation_ids),
            )
            document_ids = list(self.db.scalars(document_ids_stmt).all())
            if document_ids:
                self.db.execute(
                    delete(ChunkEmbedding).where(
                        ChunkEmbedding.team_id == user.team_id,
                        ChunkEmbedding.document_id.in_(document_ids),
                    )
                )
                self.db.execute(
                    delete(DocumentChunk).where(
                        DocumentChunk.team_id == user.team_id,
                        DocumentChunk.document_id.in_(document_ids),
                    )
                )
                self.db.execute(
                    delete(Document).where(
                        Document.team_id == user.team_id,
                        Document.conversation_id.in_(conversation_ids),
                    )
                )

        self.db.execute(
            delete(ChatHistory).where(
                ChatHistory.team_id == user.team_id,
                ChatHistory.user_id == user.user_id,
            )
        )
        self.db.execute(
            delete(Conversation).where(
                Conversation.team_id == user.team_id,
                Conversation.user_id == user.user_id,
            )
        )
        self.db.execute(
            delete(LLMModelConfig).where(
                LLMModelConfig.team_id == user.team_id,
                LLMModelConfig.user_id == user.user_id,
            )
        )
        self.db.execute(
            delete(EmbeddingModelConfig).where(
                EmbeddingModelConfig.team_id == user.team_id,
                EmbeddingModelConfig.user_id == user.user_id,
            )
        )
        self.db.execute(delete(User).where(User.user_id == user.user_id))
        self.db.commit()

    def list_conversations(
        self,
        *,
        team_id: str | None = None,
        user_id: str | None = None,
        limit: int = 300,
    ) -> list[AdminConversationItem]:
        stmt = select(Conversation).order_by(
            Conversation.is_pinned.desc(),
            Conversation.pinned_at.desc(),
            Conversation.created_at.desc(),
        )
        if team_id is not None:
            stmt = stmt.where(Conversation.team_id == team_id)
        if user_id is not None:
            stmt = stmt.where(Conversation.user_id == user_id)
        conversations = list(self.db.scalars(stmt.limit(limit)).all())
        if not conversations:
            return []

        conversation_ids = [item.conversation_id for item in conversations]
        message_count_map = self._count_map(
            select(ChatHistory.conversation_id, func.count(ChatHistory.message_id))
            .where(ChatHistory.conversation_id.in_(conversation_ids))
            .group_by(ChatHistory.conversation_id)
        )
        document_count_map = self._count_map(
            select(Document.conversation_id, func.count(Document.document_id))
            .where(Document.conversation_id.in_(conversation_ids))
            .group_by(Document.conversation_id)
        )

        return [
            AdminConversationItem(
                conversation_id=item.conversation_id,
                team_id=item.team_id,
                user_id=item.user_id,
                title=item.title,
                status=item.status,
                is_pinned=item.is_pinned,
                created_at=item.created_at,
                message_count=message_count_map.get(item.conversation_id, 0),
                document_count=document_count_map.get(item.conversation_id, 0),
            )
            for item in conversations
        ]

    def delete_conversation(self, conversation_id: str) -> None:
        conversation = self.db.get(Conversation, conversation_id)
        if conversation is None:
            raise EntityNotFoundError(f"Conversation '{conversation_id}' not found.")

        document_ids_stmt = select(Document.document_id).where(
            Document.team_id == conversation.team_id,
            Document.conversation_id == conversation_id,
        )
        document_ids = list(self.db.scalars(document_ids_stmt).all())
        if document_ids:
            self.db.execute(
                delete(ChunkEmbedding).where(
                    ChunkEmbedding.team_id == conversation.team_id,
                    ChunkEmbedding.document_id.in_(document_ids),
                )
            )
            self.db.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.team_id == conversation.team_id,
                    DocumentChunk.document_id.in_(document_ids),
                )
            )

        self.db.execute(
            delete(Document).where(
                Document.team_id == conversation.team_id,
                Document.conversation_id == conversation_id,
            )
        )
        self.db.execute(
            delete(ChatHistory).where(
                ChatHistory.team_id == conversation.team_id,
                ChatHistory.user_id == conversation.user_id,
                ChatHistory.conversation_id == conversation_id,
            )
        )
        self.db.execute(delete(Conversation).where(Conversation.conversation_id == conversation_id))
        self.db.commit()

    def list_documents(
        self,
        *,
        team_id: str | None = None,
        user_id: str | None = None,
        conversation_id: str | None = None,
        limit: int = 300,
    ) -> list[AdminDocumentItem]:
        stmt = select(Document).order_by(Document.created_at.desc())
        if team_id is not None:
            stmt = stmt.where(Document.team_id == team_id)
        if conversation_id is not None:
            stmt = stmt.where(Document.conversation_id == conversation_id)
        if user_id is not None:
            stmt = stmt.join(
                Conversation,
                and_(
                    Conversation.conversation_id == Document.conversation_id,
                    Conversation.team_id == Document.team_id,
                ),
            ).where(Conversation.user_id == user_id)

        documents = list(self.db.scalars(stmt.limit(limit)).all())
        return [self._to_document_item(item) for item in documents]

    def get_document(self, document_id: str) -> AdminDocumentDetail:
        document = self.db.get(Document, document_id)
        if document is None:
            raise EntityNotFoundError(f"Document '{document_id}' not found.")

        base = self._to_document_item(document)
        return AdminDocumentDetail(
            document_id=base.document_id,
            team_id=base.team_id,
            conversation_id=base.conversation_id,
            source_name=base.source_name,
            content_type=base.content_type,
            status=base.status,
            created_at=base.created_at,
            char_count=base.char_count,
            content_preview=base.content_preview,
            content=document.content,
        )

    def delete_document(self, document_id: str) -> None:
        document = self.db.get(Document, document_id)
        if document is None:
            raise EntityNotFoundError(f"Document '{document_id}' not found.")

        self.db.execute(
            delete(ChunkEmbedding).where(
                ChunkEmbedding.team_id == document.team_id,
                ChunkEmbedding.document_id == document.document_id,
            )
        )
        self.db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.team_id == document.team_id,
                DocumentChunk.document_id == document.document_id,
            )
        )
        self.db.execute(delete(Document).where(Document.document_id == document.document_id))
        self.db.commit()

    def _to_document_item(self, document: Document) -> AdminDocumentItem:
        normalized_content = " ".join(document.content.split())
        preview = normalized_content[:160]
        if len(normalized_content) > 160:
            preview = f"{preview}..."
        return AdminDocumentItem(
            document_id=document.document_id,
            team_id=document.team_id,
            conversation_id=document.conversation_id,
            source_name=document.source_name,
            content_type=document.content_type,
            status=document.status,
            created_at=document.created_at,
            char_count=len(document.content),
            content_preview=preview,
        )

    def _count_table(self, column: Any) -> int:
        stmt = select(func.count(column))
        return int(self.db.scalar(stmt) or 0)

    def _count_map(self, stmt: Any) -> dict[str, int]:
        rows = self.db.execute(stmt).all()
        return {str(key): int(value) for key, value in rows}

    def _count_by_user(self, *, user_id: str, team_id: str) -> int:
        stmt = select(func.count(Conversation.conversation_id)).where(
            Conversation.user_id == user_id,
            Conversation.team_id == team_id,
        )
        return int(self.db.scalar(stmt) or 0)

    def _count_documents_by_user(self, *, user_id: str, team_id: str) -> int:
        stmt = (
            select(func.count(Document.document_id))
            .join(
                Conversation,
                and_(
                    Conversation.conversation_id == Document.conversation_id,
                    Conversation.team_id == Document.team_id,
                ),
            )
            .where(
                Conversation.user_id == user_id,
                Conversation.team_id == team_id,
            )
        )
        return int(self.db.scalar(stmt) or 0)
