import hashlib
from collections.abc import Generator
from datetime import datetime, timezone

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
        embedding_model_config,
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
    table_names = set(inspector.get_table_names())

    if "conversations" in table_names:
        conversation_cols = {item["name"] for item in inspector.get_columns("conversations")}
        if "is_pinned" not in conversation_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE conversations ADD COLUMN is_pinned BOOLEAN DEFAULT 0")
        if "pinned_at" not in conversation_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE conversations ADD COLUMN pinned_at DATETIME")

    if "documents" in table_names:
        document_cols = {item["name"] for item in inspector.get_columns("documents")}
        if "conversation_id" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN conversation_id VARCHAR(36)")
        if "status" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN status VARCHAR(16) DEFAULT 'pending'")
        if "mime_type" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN mime_type VARCHAR(128)")
        if "size_bytes" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN size_bytes BIGINT")
        if "sha256" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN sha256 VARCHAR(64)")
        if "storage_key" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN storage_key VARCHAR(512)")
        if "preview_key" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN preview_key VARCHAR(512)")
        if "page_count" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN page_count INTEGER")
        if "failure_stage" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN failure_stage VARCHAR(16)")
        if "error_code" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN error_code VARCHAR(64)")
        if "error_message" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN error_message TEXT")
        if "meta_json" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN meta_json TEXT")
        if "updated_at" not in document_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN updated_at DATETIME")

        with engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_documents_team_conversation_created_at "
                "ON documents(team_id, conversation_id, created_at)"
            )
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_documents_team_status_created_at "
                "ON documents(team_id, status, created_at)"
            )
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_documents_team_sha256 "
                "ON documents(team_id, sha256)"
            )

            rows = conn.exec_driver_sql(
                """
                SELECT document_id, content_type, status, content, created_at, updated_at,
                       mime_type, size_bytes, sha256, storage_key
                FROM documents
                """
            ).mappings().all()

            now_iso = datetime.now(timezone.utc).isoformat()
            mime_by_type = {
                "txt": "text/plain",
                "md": "text/markdown",
                "pdf": "application/pdf",
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "webp": "image/webp",
            }
            allowed_statuses = {
                "pending",
                "uploaded",
                "parsing",
                "chunking",
                "indexing",
                "ready",
                "failed",
                "deleted",
            }
            for row in rows:
                content_type = str(row.get("content_type") or "md").strip().lower() or "md"
                if content_type not in mime_by_type:
                    content_type = "md"

                content = row.get("content")
                content_text = str(content) if isinstance(content, str) else ""
                if content_text:
                    digest = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
                else:
                    digest = hashlib.sha256(str(row["document_id"]).encode("utf-8")).hexdigest()

                status = str(row.get("status") or "").strip().lower() or "pending"
                if status not in allowed_statuses:
                    status = "pending"

                created_at = row.get("created_at")
                updated_at = row.get("updated_at") or created_at or now_iso
                storage_key = str(row.get("storage_key") or "").strip() or f"inline://legacy/{row['document_id']}"

                conn.exec_driver_sql(
                    """
                    UPDATE documents
                    SET content_type = :content_type,
                        status = :status,
                        mime_type = :mime_type,
                        size_bytes = :size_bytes,
                        sha256 = :sha256,
                        storage_key = :storage_key,
                        updated_at = :updated_at
                    WHERE document_id = :document_id
                    """,
                    {
                        "document_id": row["document_id"],
                        "content_type": content_type,
                        "status": status,
                        "mime_type": str(row.get("mime_type") or "").strip() or mime_by_type[content_type],
                        "size_bytes": int(row.get("size_bytes") or len(content_text.encode("utf-8"))),
                        "sha256": str(row.get("sha256") or "").strip() or digest,
                        "storage_key": storage_key,
                        "updated_at": updated_at,
                    },
                )

    if "document_chunks" in table_names:
        chunk_cols = {item["name"] for item in inspector.get_columns("document_chunks")}
        if "page_no" not in chunk_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE document_chunks ADD COLUMN page_no INTEGER")
        if "locator_label" not in chunk_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE document_chunks ADD COLUMN locator_label VARCHAR(64)")
        if "block_type" not in chunk_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE document_chunks ADD COLUMN block_type VARCHAR(16)")
        if "meta_json" not in chunk_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE document_chunks ADD COLUMN meta_json TEXT")
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_document_chunks_document_page_chunk "
                "ON document_chunks(document_id, page_no, chunk_index)"
            )

    if "chat_history" in table_names:
        history_cols = {item["name"] for item in inspector.get_columns("chat_history")}
        if "conversation_id" not in history_cols:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE chat_history ADD COLUMN conversation_id VARCHAR(36)")
