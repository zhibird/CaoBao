from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class ChunkService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def chunk_document(
        self,
        document_id: str,
        team_id: str,
        conversation_id: str | None,
        max_chars: int,
        overlap: int,
    ) -> list[DocumentChunk]:
        if overlap >= max_chars:
            raise DomainValidationError("overlap must be smaller than max_chars.")

        document = self._get_document_in_team(
            document_id=document_id,
            team_id=team_id,
            conversation_id=conversation_id,
        )
        pieces = self._split_text(
            text=document.content,
            max_chars=max_chars,
            overlap=overlap,
        )

        # Re-chunking should invalidate existing embeddings for this document.
        self.db.execute(
            delete(ChunkEmbedding).where(
                ChunkEmbedding.document_id == document_id,
                ChunkEmbedding.team_id == team_id,
            )
        )

        self.db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.team_id == team_id,
            )
        )

        chunks: list[DocumentChunk] = []
        for index, (content, start_char, end_char) in enumerate(pieces):
            chunk = DocumentChunk(
                chunk_id=str(uuid4()),
                document_id=document_id,
                team_id=team_id,
                chunk_index=index,
                content=content,
                start_char=start_char,
                end_char=end_char,
            )
            chunks.append(chunk)

        self.db.add_all(chunks)
        self.db.commit()

        return self.list_chunks(
            document_id=document_id,
            team_id=team_id,
            conversation_id=conversation_id,
        )

    def list_chunks(
        self,
        document_id: str,
        team_id: str,
        conversation_id: str | None,
    ) -> list[DocumentChunk]:
        self._get_document_in_team(
            document_id=document_id,
            team_id=team_id,
            conversation_id=conversation_id,
        )

        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.team_id == team_id,
            )
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(self.db.scalars(stmt).all())

    def _get_document_in_team(
        self,
        document_id: str,
        team_id: str,
        conversation_id: str | None,
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

    def _split_text(self, text: str, max_chars: int, overlap: int) -> list[tuple[str, int, int]]:
        normalized = text.strip()
        if not normalized:
            raise DomainValidationError("Document content is empty.")

        pieces: list[tuple[str, int, int]] = []
        start = 0
        total_len = len(normalized)

        while start < total_len:
            end = min(start + max_chars, total_len)

            if end < total_len:
                split_pos = normalized.rfind("\n\n", start, end)
                if split_pos == -1:
                    split_pos = normalized.rfind("\n", start, end)
                if split_pos == -1:
                    split_pos = normalized.rfind(" ", start, end)

                if split_pos > start + (max_chars // 2):
                    end = split_pos

            chunk_text = normalized[start:end].strip()
            if chunk_text:
                pieces.append((chunk_text, start, end))

            if end >= total_len:
                break

            next_start = end - overlap
            if next_start <= start:
                next_start = end
            start = next_start

        return pieces
