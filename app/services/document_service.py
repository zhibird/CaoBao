from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundError
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.team import Team
from app.schemas.document import DocumentImportRequest


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def import_document(self, payload: DocumentImportRequest) -> Document:
        team = self.db.get(Team, payload.team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{payload.team_id}' does not exist.")

        if payload.conversation_id is not None:
            conversation = self.db.get(Conversation, payload.conversation_id)
            if conversation is None:
                raise EntityNotFoundError(f"Conversation '{payload.conversation_id}' does not exist.")
            if conversation.team_id != payload.team_id:
                raise EntityNotFoundError(
                    f"Conversation '{payload.conversation_id}' does not belong to team '{payload.team_id}'."
                )

        document = Document(
            document_id=str(uuid4()),
            team_id=payload.team_id,
            conversation_id=payload.conversation_id,
            source_name=payload.source_name,
            content_type=payload.content_type,
            content=payload.content,
            # Use Python-side timestamp to preserve microseconds for deterministic recency ordering.
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def list_documents(self, team_id: str, conversation_id: str | None = None) -> list[Document]:
        stmt = select(Document).where(Document.team_id == team_id)
        if conversation_id is not None:
            stmt = stmt.where(Document.conversation_id == conversation_id)
        stmt = stmt.order_by(Document.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_document_in_team(
        self,
        document_id: str,
        team_id: str,
        conversation_id: str | None = None,
    ) -> Document:
        stmt = select(Document).where(
            Document.document_id == document_id,
            Document.team_id == team_id,
        )
        if conversation_id is not None:
            stmt = stmt.where(Document.conversation_id == conversation_id)
        document = self.db.scalar(stmt)
        if document is None:
            raise EntityNotFoundError(
                f"Document '{document_id}' not found in team '{team_id}'."
            )

        return document
