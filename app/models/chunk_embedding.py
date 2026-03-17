from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document_chunk import DocumentChunk


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (UniqueConstraint("chunk_id", name="uq_chunk_embedding_chunk_id"),)

    embedding_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("document_chunks.chunk_id"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.document_id"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True,
    )
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False)
    vector_json: Mapped[str] = mapped_column(Text, nullable=False)
    vector_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunk: Mapped["DocumentChunk"] = relationship(back_populates="embedding")