import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundError
from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.team import Team
from app.services.embedding_service import EmbeddingService


class RetrievalService:
    def __init__(self, db: Session, embedding_service: EmbeddingService) -> None:
        self.db = db
        self.embedding_service = embedding_service

    def index_chunks(
        self,
        team_id: str,
        document_id: str | None = None,
        conversation_id: str | None = None,
    ) -> int:
        self._ensure_team_exists(team_id=team_id)

        stmt = select(DocumentChunk).where(DocumentChunk.team_id == team_id)
        if conversation_id is not None:
            stmt = stmt.join(Document, Document.document_id == DocumentChunk.document_id).where(
                Document.conversation_id == conversation_id
            )
        if document_id is not None:
            stmt = stmt.where(DocumentChunk.document_id == document_id)

        chunks = list(self.db.scalars(stmt).all())
        if not chunks:
            raise EntityNotFoundError("No chunks found. Run document chunking first.")

        for chunk in chunks:
            vector = self.embedding_service.embed_text(chunk.content)
            payload = json.dumps(vector, separators=(",", ":"))

            existing = self.db.scalar(
                select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk.chunk_id)
            )
            if existing is None:
                existing = ChunkEmbedding(
                    embedding_id=str(uuid4()),
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    team_id=chunk.team_id,
                    embedding_model=self.embedding_service.model_name,
                    vector_json=payload,
                    vector_dim=self.embedding_service.dim,
                )
                self.db.add(existing)
            else:
                existing.document_id = chunk.document_id
                existing.team_id = chunk.team_id
                existing.embedding_model = self.embedding_service.model_name
                existing.vector_json = payload
                existing.vector_dim = self.embedding_service.dim

        self.db.commit()
        return len(chunks)

    def search_chunks(
        self,
        team_id: str,
        query: str,
        top_k: int,
        document_id: str | None = None,
        conversation_id: str | None = None,
    ) -> list[dict[str, object]]:
        self._ensure_team_exists(team_id=team_id)

        query_vec = self.embedding_service.embed_text(query)

        stmt = (
            select(ChunkEmbedding, DocumentChunk)
            .join(DocumentChunk, ChunkEmbedding.chunk_id == DocumentChunk.chunk_id)
            .where(ChunkEmbedding.team_id == team_id)
        )
        if conversation_id is not None:
            stmt = stmt.join(Document, Document.document_id == ChunkEmbedding.document_id).where(
                Document.conversation_id == conversation_id
            )
        if document_id is not None:
            stmt = stmt.where(ChunkEmbedding.document_id == document_id)

        rows = self.db.execute(stmt).all()
        if not rows:
            raise EntityNotFoundError("No indexed chunks found. Run retrieval indexing first.")

        scored_hits: list[dict[str, object]] = []
        for embedding, chunk in rows:
            vector = json.loads(embedding.vector_json)
            score = self.embedding_service.cosine_similarity(query_vec, vector)
            scored_hits.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "team_id": chunk.team_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "score": round(score, 6),
                }
            )

        scored_hits.sort(key=lambda item: item["score"], reverse=True)
        return scored_hits[:top_k]

    def has_indexed_chunks(
        self,
        team_id: str,
        document_id: str | None = None,
        conversation_id: str | None = None,
    ) -> bool:
        """Check whether indexed chunks exist for the team/document scope."""
        self._ensure_team_exists(team_id=team_id)

        stmt = select(ChunkEmbedding.embedding_id).where(ChunkEmbedding.team_id == team_id)
        if conversation_id is not None:
            stmt = stmt.join(Document, Document.document_id == ChunkEmbedding.document_id).where(
                Document.conversation_id == conversation_id
            )
        if document_id is not None:
            stmt = stmt.where(ChunkEmbedding.document_id == document_id)

        first_embedding_id = self.db.scalar(stmt.limit(1))
        return first_embedding_id is not None

    def _ensure_team_exists(self, team_id: str) -> None:
        team = self.db.get(Team, team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{team_id}' does not exist.")
