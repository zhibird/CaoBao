from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document_chunk import DocumentChunk
    from app.models.team import Team


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_team_conversation_created_at", "team_id", "conversation_id", "created_at"),
        Index("ix_documents_team_status_created_at", "team_id", "status", "created_at"),
        Index("ix_documents_team_sha256", "team_id", "sha256"),
    )

    document_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.conversation_id"),
        nullable=True,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="text/plain")
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    preview_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_stage: Mapped[str | None] = mapped_column(String(16), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="uploaded")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    team: Mapped["Team"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
