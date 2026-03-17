from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False, default="P2")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
