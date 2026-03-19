from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()

is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    future=True,
)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import (  # noqa: F401
        chat_history,
        chunk_embedding,
        conversation,
        document,
        document_chunk,
        incident,
        llm_model_config,
        team,
        user,
    )

    Base.metadata.create_all(bind=engine)
    _ensure_phase1_columns()


def _ensure_phase1_columns() -> None:
    """Best-effort lightweight migration for existing DB files."""
    inspector = inspect(engine)

    if "conversations" in inspector.get_table_names():
        conversation_cols = {item["name"] for item in inspector.get_columns("conversations")}
        if "is_pinned" not in conversation_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE conversations ADD COLUMN is_pinned BOOLEAN DEFAULT 0")
        if "pinned_at" not in conversation_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE conversations ADD COLUMN pinned_at DATETIME")

    if "documents" in inspector.get_table_names():
        document_cols = {item["name"] for item in inspector.get_columns("documents")}
        if "conversation_id" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN conversation_id VARCHAR(36)")

    if "chat_history" in inspector.get_table_names():
        history_cols = {item["name"] for item in inspector.get_columns("chat_history")}
        if "conversation_id" not in history_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE chat_history ADD COLUMN conversation_id VARCHAR(36)")
