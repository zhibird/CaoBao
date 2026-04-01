from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnswerFavorite(Base):
    __tablename__ = "answer_favorites"
    __table_args__ = (
        Index(
            "ix_answer_favorites_team_space_user_created_at",
            "team_id",
            "space_id",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_answer_favorites_team_conversation_created_at",
            "team_id",
            "conversation_id",
            "created_at",
        ),
    )

    favorite_id: Mapped[str] = mapped_column(String(36), primary_key=True)
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
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.conversation_id"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[str] = mapped_column(
        ForeignKey("chat_history.message_id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_promoted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
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
