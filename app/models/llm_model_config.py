from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LLMModelConfig(Base):
    __tablename__ = "llm_model_configs"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", "model_name", name="uq_llm_model_team_user_name"),
    )

    config_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
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
