"""bootstrap core schema for alembic-first deployments

Revision ID: 20260330_00
Revises:
Create Date: 2026-03-30 16:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260330_00"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())

    if "teams" not in table_names:
        op.create_table(
            "teams",
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("team_id"),
        )

    if "users" not in table_names:
        op.create_table(
            "users",
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("display_name", sa.String(length=128), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False, server_default="member"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.PrimaryKeyConstraint("user_id"),
        )
    _ensure_index("users", "ix_users_team_id", ["team_id"])

    if "project_spaces" not in table_names:
        op.create_table(
            "project_spaces",
            sa.Column("space_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("owner_user_id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.user_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.PrimaryKeyConstraint("space_id"),
        )
    _ensure_index("project_spaces", "ix_project_spaces_team_id", ["team_id"])
    _ensure_index("project_spaces", "ix_project_spaces_owner_user_id", ["owner_user_id"])
    _ensure_index("project_spaces", "ix_project_spaces_status", ["status"])
    _ensure_index("project_spaces", "ix_project_spaces_is_default", ["is_default"])

    if "conversations" not in table_names:
        op.create_table(
            "conversations",
            sa.Column("conversation_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("space_id", sa.String(length=36), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
            sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["space_id"], ["project_spaces.space_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.PrimaryKeyConstraint("conversation_id"),
        )
    else:
        _ensure_column(
            "conversations",
            "space_id",
            sa.Column("space_id", sa.String(length=36), nullable=True),
        )
        _ensure_column(
            "conversations",
            "is_pinned",
            sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        _ensure_column(
            "conversations",
            "pinned_at",
            sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        )
    _ensure_index("conversations", "ix_conversations_team_id", ["team_id"])
    _ensure_index("conversations", "ix_conversations_user_id", ["user_id"])
    _ensure_index("conversations", "ix_conversations_space_id", ["space_id"])
    _ensure_index("conversations", "ix_conversations_status", ["status"])
    _ensure_index("conversations", "ix_conversations_is_pinned", ["is_pinned"])

    if "documents" not in table_names:
        op.create_table(
            "documents",
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("conversation_id", sa.String(length=36), nullable=True),
            sa.Column("space_id", sa.String(length=36), nullable=True),
            sa.Column("source_name", sa.String(length=255), nullable=False),
            sa.Column("content_type", sa.String(length=32), nullable=False),
            sa.Column("mime_type", sa.String(length=128), nullable=False, server_default="text/plain"),
            sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("sha256", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("storage_key", sa.String(length=512), nullable=False, server_default=""),
            sa.Column("preview_key", sa.String(length=512), nullable=True),
            sa.Column("page_count", sa.Integer(), nullable=True),
            sa.Column("failure_stage", sa.String(length=16), nullable=True),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("meta_json", sa.Text(), nullable=True),
            sa.Column("visibility", sa.String(length=16), nullable=False, server_default="conversation"),
            sa.Column("asset_kind", sa.String(length=32), nullable=False, server_default="attachment"),
            sa.Column("retrieval_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("origin_document_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="uploaded"),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.conversation_id"]),
            sa.ForeignKeyConstraint(["origin_document_id"], ["documents.document_id"]),
            sa.ForeignKeyConstraint(["space_id"], ["project_spaces.space_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.PrimaryKeyConstraint("document_id"),
        )
    else:
        _ensure_column("documents", "conversation_id", sa.Column("conversation_id", sa.String(length=36), nullable=True))
        _ensure_column("documents", "space_id", sa.Column("space_id", sa.String(length=36), nullable=True))
        _ensure_column(
            "documents",
            "mime_type",
            sa.Column("mime_type", sa.String(length=128), nullable=False, server_default="text/plain"),
        )
        _ensure_column("documents", "size_bytes", sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"))
        _ensure_column("documents", "sha256", sa.Column("sha256", sa.String(length=64), nullable=False, server_default=""))
        _ensure_column(
            "documents",
            "storage_key",
            sa.Column("storage_key", sa.String(length=512), nullable=False, server_default=""),
        )
        _ensure_column("documents", "preview_key", sa.Column("preview_key", sa.String(length=512), nullable=True))
        _ensure_column("documents", "page_count", sa.Column("page_count", sa.Integer(), nullable=True))
        _ensure_column("documents", "failure_stage", sa.Column("failure_stage", sa.String(length=16), nullable=True))
        _ensure_column("documents", "error_code", sa.Column("error_code", sa.String(length=64), nullable=True))
        _ensure_column("documents", "error_message", sa.Column("error_message", sa.Text(), nullable=True))
        _ensure_column("documents", "meta_json", sa.Column("meta_json", sa.Text(), nullable=True))
        _ensure_column(
            "documents",
            "visibility",
            sa.Column("visibility", sa.String(length=16), nullable=False, server_default="conversation"),
        )
        _ensure_column(
            "documents",
            "asset_kind",
            sa.Column("asset_kind", sa.String(length=32), nullable=False, server_default="attachment"),
        )
        _ensure_column(
            "documents",
            "retrieval_enabled",
            sa.Column("retrieval_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        _ensure_column(
            "documents",
            "origin_document_id",
            sa.Column("origin_document_id", sa.String(length=36), nullable=True),
        )
        _ensure_column("documents", "status", sa.Column("status", sa.String(length=16), nullable=False, server_default="uploaded"))
        _ensure_column("documents", "updated_at", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_index("documents", "ix_documents_team_id", ["team_id"])
    _ensure_index("documents", "ix_documents_conversation_id", ["conversation_id"])
    _ensure_index("documents", "ix_documents_space_id", ["space_id"])
    _ensure_index("documents", "ix_documents_visibility", ["visibility"])
    _ensure_index("documents", "ix_documents_asset_kind", ["asset_kind"])
    _ensure_index("documents", "ix_documents_retrieval_enabled", ["retrieval_enabled"])
    _ensure_index("documents", "ix_documents_origin_document_id", ["origin_document_id"])
    _ensure_index("documents", "ix_documents_team_conversation_created_at", ["team_id", "conversation_id", "created_at"])
    _ensure_index("documents", "ix_documents_team_status_created_at", ["team_id", "status", "created_at"])
    _ensure_index("documents", "ix_documents_team_sha256", ["team_id", "sha256"])
    _ensure_index("documents", "ix_documents_team_space_visibility_created_at", ["team_id", "space_id", "visibility", "created_at"])

    if "document_chunks" not in table_names:
        op.create_table(
            "document_chunks",
            sa.Column("chunk_id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("start_char", sa.Integer(), nullable=False),
            sa.Column("end_char", sa.Integer(), nullable=False),
            sa.Column("page_no", sa.Integer(), nullable=True),
            sa.Column("locator_label", sa.String(length=64), nullable=True),
            sa.Column("block_type", sa.String(length=16), nullable=True),
            sa.Column("meta_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.PrimaryKeyConstraint("chunk_id"),
            sa.UniqueConstraint("document_id", "chunk_index", name="uq_doc_chunk_index"),
        )
    else:
        _ensure_column("document_chunks", "page_no", sa.Column("page_no", sa.Integer(), nullable=True))
        _ensure_column("document_chunks", "locator_label", sa.Column("locator_label", sa.String(length=64), nullable=True))
        _ensure_column("document_chunks", "block_type", sa.Column("block_type", sa.String(length=16), nullable=True))
        _ensure_column("document_chunks", "meta_json", sa.Column("meta_json", sa.Text(), nullable=True))
    _ensure_index("document_chunks", "ix_document_chunks_document_id", ["document_id"])
    _ensure_index("document_chunks", "ix_document_chunks_team_id", ["team_id"])
    _ensure_index("document_chunks", "ix_document_chunks_document_page_chunk", ["document_id", "page_no", "chunk_index"])

    if "chunk_embeddings" not in table_names:
        op.create_table(
            "chunk_embeddings",
            sa.Column("embedding_id", sa.String(length=36), nullable=False),
            sa.Column("chunk_id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("embedding_model", sa.String(length=64), nullable=False),
            sa.Column("vector_json", sa.Text(), nullable=False),
            sa.Column("vector_dim", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.chunk_id"]),
            sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.PrimaryKeyConstraint("embedding_id"),
            sa.UniqueConstraint("chunk_id", name="uq_chunk_embedding_chunk_id"),
        )
    _ensure_index("chunk_embeddings", "ix_chunk_embeddings_chunk_id", ["chunk_id"])
    _ensure_index("chunk_embeddings", "ix_chunk_embeddings_document_id", ["document_id"])
    _ensure_index("chunk_embeddings", "ix_chunk_embeddings_team_id", ["team_id"])

    if "chat_history" not in table_names:
        op.create_table(
            "chat_history",
            sa.Column("message_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("conversation_id", sa.String(length=36), nullable=True),
            sa.Column("space_id", sa.String(length=36), nullable=True),
            sa.Column("channel", sa.String(length=16), nullable=False),
            sa.Column("request_text", sa.Text(), nullable=False),
            sa.Column("response_text", sa.Text(), nullable=False),
            sa.Column("request_payload_json", sa.Text(), nullable=False),
            sa.Column("response_payload_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.conversation_id"]),
            sa.ForeignKeyConstraint(["space_id"], ["project_spaces.space_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.PrimaryKeyConstraint("message_id"),
        )
    else:
        _ensure_column("chat_history", "conversation_id", sa.Column("conversation_id", sa.String(length=36), nullable=True))
        _ensure_column("chat_history", "space_id", sa.Column("space_id", sa.String(length=36), nullable=True))
    _ensure_index("chat_history", "ix_chat_history_team_id", ["team_id"])
    _ensure_index("chat_history", "ix_chat_history_user_id", ["user_id"])
    _ensure_index("chat_history", "ix_chat_history_conversation_id", ["conversation_id"])
    _ensure_index("chat_history", "ix_chat_history_space_id", ["space_id"])

    if "llm_model_configs" not in table_names:
        op.create_table(
            "llm_model_configs",
            sa.Column("config_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("model_name", sa.String(length=128), nullable=False),
            sa.Column("base_url", sa.String(length=255), nullable=False),
            sa.Column("api_key", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.PrimaryKeyConstraint("config_id"),
            sa.UniqueConstraint("team_id", "user_id", "model_name", name="uq_llm_model_team_user_name"),
        )
    _ensure_index("llm_model_configs", "ix_llm_model_configs_team_id", ["team_id"])
    _ensure_index("llm_model_configs", "ix_llm_model_configs_user_id", ["user_id"])

    if "embedding_model_configs" not in table_names:
        op.create_table(
            "embedding_model_configs",
            sa.Column("config_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("model_name", sa.String(length=128), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("base_url", sa.String(length=255), nullable=True),
            sa.Column("api_key", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.PrimaryKeyConstraint("config_id"),
            sa.UniqueConstraint("team_id", "user_id", "model_name", name="uq_embedding_model_team_user_name"),
        )
    _ensure_index("embedding_model_configs", "ix_embedding_model_configs_team_id", ["team_id"])
    _ensure_index("embedding_model_configs", "ix_embedding_model_configs_user_id", ["user_id"])

    if "incidents" not in table_names:
        op.create_table(
            "incidents",
            sa.Column("incident_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("created_by_user_id", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("severity", sa.String(length=8), nullable=False, server_default="P2"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.user_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.PrimaryKeyConstraint("incident_id"),
        )
    _ensure_index("incidents", "ix_incidents_team_id", ["team_id"])
    _ensure_index("incidents", "ix_incidents_created_by_user_id", ["created_by_user_id"])


def _ensure_column(table_name: str, column_name: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    current_columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column_name not in current_columns:
        op.add_column(table_name, column)


def _ensure_index(table_name: str, index_name: str, columns: list[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        return
    index_names = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in index_names:
        op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    # Bootstrap revision is intentionally kept as a no-op on downgrade.
    # Core tables are shared by the application and should not be dropped by default.
    return
