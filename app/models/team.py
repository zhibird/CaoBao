from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.user import User


class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )