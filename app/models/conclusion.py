from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Conclusion(Base):
    __tablename__ = "conclusions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'effective', 'superseded', 'archived')",
            name="ck_conclusions_status",
        ),
        Index(
            "ix_conclusions_team_space_status_updated_at",
            "team_id",
            "space_id",
            "status",
            "updated_at",
        ),
        Index(
            "ix_conclusions_team_topic_created_at",
            "team_id",
            "topic",
            "created_at",
        ),
    )

    conclusion_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True,
    )
    space_id: Mapped[str] = mapped_column(
        ForeignKey("project_spaces.space_id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("chat_history.message_id"),
        nullable=True,
        index=True,
    )
    source_favorite_id: Mapped[str | None] = mapped_column(
        ForeignKey("answer_favorites.favorite_id"),
        nullable=True,
        index=True,
    )
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_sync_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.document_id"),
        nullable=True,
        index=True,
    )
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

