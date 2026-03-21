import json
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.team import Team
from app.services.embedding_model_service import EmbeddingModelService
from app.services.embedding_service import EmbeddingRuntimeConfig, EmbeddingService


class RetrievalService:
    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService,
        embedding_model_service: EmbeddingModelService,
    ) -> None:
        self.db = db
        self.embedding_service = embedding_service
        self.embedding_model_service = embedding_model_service

    def index_chunks(
        self,
        team_id: str,
        document_id: str | None = None,
        document_ids: list[str] | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        embedding_model: str | None = None,
        rebuild: bool = False,
    ) -> int:
        self._ensure_team_exists(team_id=team_id)
        scoped_document_ids = self._resolve_document_ids(
            document_id=document_id,
            document_ids=document_ids,
        )
        target_documents = self._load_target_documents(
            team_id=team_id,
            conversation_id=conversation_id,
            document_ids=scoped_document_ids,
        )
        if not target_documents:
            raise EntityNotFoundError("No documents found for indexing scope.")

        for document in target_documents:
            document.status = "indexing"
            self.db.add(document)
        self.db.commit()

        runtime_embedding = self._resolve_embedding_runtime(
            team_id=team_id,
            user_id=user_id,
            embedding_model=embedding_model,
        )

        try:
            if rebuild:
                self._delete_scope_embeddings(
                    team_id=team_id,
                    document_id=document_id,
                    document_ids=scoped_document_ids,
                    conversation_id=conversation_id,
                )

            stmt = select(DocumentChunk).where(DocumentChunk.team_id == team_id)
            if conversation_id is not None:
                stmt = stmt.join(Document, Document.document_id == DocumentChunk.document_id).where(
                    Document.conversation_id == conversation_id
                )
            if scoped_document_ids is not None:
                stmt = stmt.where(DocumentChunk.document_id.in_(scoped_document_ids))

            chunks = list(self.db.scalars(stmt).all())
            if not chunks:
                raise EntityNotFoundError("No chunks found. Run document chunking first.")

            batch_size = max(1, self.embedding_service.batch_size)
            for start in range(0, len(chunks), batch_size):
                chunk_batch = chunks[start : start + batch_size]
                texts = [chunk.content for chunk in chunk_batch]
                vectors = self.embedding_service.embed_texts(texts, runtime=runtime_embedding)
                if len(vectors) != len(chunk_batch):
                    raise DomainValidationError(
                        f"Embedding count mismatch for index batch: expected {len(chunk_batch)}, got {len(vectors)}."
                    )

                for chunk, vector in zip(chunk_batch, vectors):
                    payload = json.dumps(vector, separators=(",", ":"))
                    vector_dim = len(vector)
                    if vector_dim <= 0:
                        raise DomainValidationError("Embedding vector cannot be empty.")

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
                            vector_dim=vector_dim,
                        )
                        self.db.add(existing)
                    else:
                        existing.document_id = chunk.document_id
                        existing.team_id = chunk.team_id
                        existing.embedding_model = self.embedding_service.model_name
                        existing.vector_json = payload
                        existing.vector_dim = vector_dim

            for document in target_documents:
                document.status = "ready"
                self.db.add(document)
            self.db.commit()
            return len(chunks)
        except Exception:
            for document in target_documents:
                document.status = "failed"
                self.db.add(document)
            self.db.commit()
            raise

    def search_chunks(
        self,
        team_id: str,
        query: str,
        top_k: int,
        document_id: str | None = None,
        document_ids: list[str] | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        embedding_model: str | None = None,
    ) -> list[dict[str, object]]:
        self._ensure_team_exists(team_id=team_id)
        scoped_document_ids = self._resolve_document_ids(
            document_id=document_id,
            document_ids=document_ids,
        )
        runtime_embedding = self._resolve_embedding_runtime(
            team_id=team_id,
            user_id=user_id,
            embedding_model=embedding_model,
        )

        query_vec = self.embedding_service.embed_text(query, runtime=runtime_embedding)

        stmt = (
            select(ChunkEmbedding, DocumentChunk, Document)
            .join(DocumentChunk, ChunkEmbedding.chunk_id == DocumentChunk.chunk_id)
            .join(Document, Document.document_id == ChunkEmbedding.document_id)
            .where(ChunkEmbedding.team_id == team_id)
        )
        if conversation_id is not None:
            stmt = stmt.where(Document.conversation_id == conversation_id)
        if scoped_document_ids is not None:
            stmt = stmt.where(ChunkEmbedding.document_id.in_(scoped_document_ids))

        rows = self.db.execute(stmt).all()
        if not rows:
            raise EntityNotFoundError("No indexed chunks found. Run retrieval indexing first.")

        scored_hits: list[dict[str, object]] = []
        query_dim = len(query_vec)
        for embedding, chunk, document in rows:
            vector = json.loads(embedding.vector_json)
            if not isinstance(vector, list):
                raise DomainValidationError(
                    "Indexed vector payload is invalid. Rebuild retrieval index with current embedding model."
                )
            if len(vector) != query_dim:
                raise DomainValidationError(
                    "Embedding dimension mismatch detected. Rebuild retrieval index with current embedding model."
                )
            score = self.embedding_service.cosine_similarity(query_vec, vector)
            scored_hits.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "source_name": document.source_name,
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
        document_ids: list[str] | None = None,
        conversation_id: str | None = None,
    ) -> bool:
        self._ensure_team_exists(team_id=team_id)
        scoped_document_ids = self._resolve_document_ids(
            document_id=document_id,
            document_ids=document_ids,
        )

        stmt = select(ChunkEmbedding.embedding_id).where(ChunkEmbedding.team_id == team_id)
        if conversation_id is not None:
            stmt = stmt.join(Document, Document.document_id == ChunkEmbedding.document_id).where(
                Document.conversation_id == conversation_id
            )
        if scoped_document_ids is not None:
            stmt = stmt.where(ChunkEmbedding.document_id.in_(scoped_document_ids))

        first_embedding_id = self.db.scalar(stmt.limit(1))
        return first_embedding_id is not None

    def _resolve_embedding_runtime(
        self,
        *,
        team_id: str,
        user_id: str | None,
        embedding_model: str | None,
    ) -> EmbeddingRuntimeConfig | None:
        normalized = (embedding_model or "").strip()
        if not normalized or normalized.lower() == "default":
            return None

        if normalized.lower() in {"mock", "none"}:
            return EmbeddingRuntimeConfig.mock_default()

        if not user_id:
            raise DomainValidationError("user_id is required when embedding_model is specified.")

        return self.embedding_model_service.resolve_runtime_config(
            team_id=team_id,
            user_id=user_id,
            model_name=normalized,
        )

    def _ensure_team_exists(self, team_id: str) -> None:
        team = self.db.get(Team, team_id)
        if team is None:
            raise EntityNotFoundError(f"Team '{team_id}' does not exist.")

    def _delete_scope_embeddings(
        self,
        *,
        team_id: str,
        document_id: str | None,
        document_ids: list[str] | None,
        conversation_id: str | None,
    ) -> None:
        scoped_document_ids = self._resolve_document_ids(
            document_id=document_id,
            document_ids=document_ids,
        )

        if scoped_document_ids is not None:
            self.db.execute(
                delete(ChunkEmbedding).where(
                    ChunkEmbedding.team_id == team_id,
                    ChunkEmbedding.document_id.in_(scoped_document_ids),
                )
            )
            return

        if conversation_id is not None:
            conversation_document_ids = list(
                self.db.scalars(
                    select(Document.document_id).where(
                        Document.team_id == team_id,
                        Document.conversation_id == conversation_id,
                    )
                ).all()
            )
            if conversation_document_ids:
                self.db.execute(
                    delete(ChunkEmbedding).where(
                        ChunkEmbedding.team_id == team_id,
                        ChunkEmbedding.document_id.in_(conversation_document_ids),
                    )
                )
            return

        self.db.execute(delete(ChunkEmbedding).where(ChunkEmbedding.team_id == team_id))

    def _resolve_document_ids(
        self,
        *,
        document_id: str | None,
        document_ids: list[str] | None,
    ) -> list[str] | None:
        values: list[str] = []
        if document_id:
            values.append(document_id)
        if document_ids:
            values.extend(document_ids)

        deduped: list[str] = []
        for item in values:
            normalized = str(item).strip()
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped or None

    def _load_target_documents(
        self,
        *,
        team_id: str,
        conversation_id: str | None,
        document_ids: list[str] | None,
    ) -> list[Document]:
        stmt = select(Document).where(Document.team_id == team_id)
        if conversation_id is not None:
            stmt = stmt.where(Document.conversation_id == conversation_id)
        if document_ids is not None:
            stmt = stmt.where(Document.document_id.in_(document_ids))
        return list(self.db.scalars(stmt).all())
