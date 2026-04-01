from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MemoryCardEmbedding(Base):
    __tablename__ = "memory_card_embeddings"
    __table_args__ = (
        Index(
            "ix_memory_card_embeddings_team_space_memory",
            "team_id",
            "space_id",
            "memory_id",
        ),
        Index(
            "ix_memory_card_embeddings_team_model_updated_at",
            "team_id",
            "embedding_model",
            "updated_at",
        ),
    )

    embedding_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    memory_id: Mapped[str] = mapped_column(
        ForeignKey("memory_cards.memory_id"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True,
    )
    space_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_spaces.space_id"),
        nullable=True,
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
