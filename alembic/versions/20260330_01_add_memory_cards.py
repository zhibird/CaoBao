"""add memory cards and embeddings

Revision ID: 20260330_01
Revises:
Create Date: 2026-03-30 09:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260330_01"
down_revision: Union[str, None] = "20260330_00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())

    if "memory_cards" not in table_names:
        op.create_table(
            "memory_cards",
            sa.Column("memory_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("space_id", sa.String(length=36), nullable=True),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("scope_level", sa.String(length=16), nullable=False, server_default="space"),
            sa.Column("category", sa.String(length=32), nullable=False, server_default="fact"),
            sa.Column("title", sa.String(length=128), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("weight", sa.Float(), nullable=False, server_default="0.8"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
            sa.Column("source_message_id", sa.String(length=36), nullable=True),
            sa.Column("source_document_id", sa.String(length=36), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "status IN ('active', 'disabled', 'expired')",
                name="ck_memory_cards_status",
            ),
            sa.CheckConstraint(
                "scope_level IN ('space', 'global')",
                name="ck_memory_cards_scope_level",
            ),
            sa.ForeignKeyConstraint(["space_id"], ["project_spaces.space_id"]),
            sa.ForeignKeyConstraint(["source_document_id"], ["documents.document_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.PrimaryKeyConstraint("memory_id"),
        )
    _ensure_index("memory_cards", op.f("ix_memory_cards_space_id"), ["space_id"])
    _ensure_index("memory_cards", op.f("ix_memory_cards_source_document_id"), ["source_document_id"])
    _ensure_index("memory_cards", op.f("ix_memory_cards_status"), ["status"])
    _ensure_index("memory_cards", op.f("ix_memory_cards_team_id"), ["team_id"])
    _ensure_index("memory_cards", op.f("ix_memory_cards_user_id"), ["user_id"])
    _ensure_index(
        "memory_cards",
        "ix_memory_cards_team_space_status_updated_at",
        ["team_id", "space_id", "status", "updated_at"],
    )
    _ensure_index(
        "memory_cards",
        "ix_memory_cards_team_user_status_created_at",
        ["team_id", "user_id", "status", "created_at"],
    )

    if "memory_card_embeddings" not in table_names:
        op.create_table(
            "memory_card_embeddings",
            sa.Column("embedding_id", sa.String(length=36), nullable=False),
            sa.Column("memory_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("space_id", sa.String(length=36), nullable=True),
            sa.Column("embedding_model", sa.String(length=64), nullable=False),
            sa.Column("vector_json", sa.Text(), nullable=False),
            sa.Column("vector_dim", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["memory_id"], ["memory_cards.memory_id"]),
            sa.ForeignKeyConstraint(["space_id"], ["project_spaces.space_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.PrimaryKeyConstraint("embedding_id"),
        )
    _ensure_index("memory_card_embeddings", op.f("ix_memory_card_embeddings_memory_id"), ["memory_id"])
    _ensure_index("memory_card_embeddings", op.f("ix_memory_card_embeddings_space_id"), ["space_id"])
    _ensure_index("memory_card_embeddings", op.f("ix_memory_card_embeddings_team_id"), ["team_id"])
    _ensure_index(
        "memory_card_embeddings",
        "ix_memory_card_embeddings_team_space_memory",
        ["team_id", "space_id", "memory_id"],
    )
    _ensure_index(
        "memory_card_embeddings",
        "ix_memory_card_embeddings_team_model_updated_at",
        ["team_id", "embedding_model", "updated_at"],
    )


def _ensure_index(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        return
    index_names = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in index_names:
        op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_memory_card_embeddings_team_model_updated_at", table_name="memory_card_embeddings")
    op.drop_index("ix_memory_card_embeddings_team_space_memory", table_name="memory_card_embeddings")
    op.drop_index(op.f("ix_memory_card_embeddings_team_id"), table_name="memory_card_embeddings")
    op.drop_index(op.f("ix_memory_card_embeddings_space_id"), table_name="memory_card_embeddings")
    op.drop_index(op.f("ix_memory_card_embeddings_memory_id"), table_name="memory_card_embeddings")
    op.drop_table("memory_card_embeddings")

    op.drop_index("ix_memory_cards_team_user_status_created_at", table_name="memory_cards")
    op.drop_index("ix_memory_cards_team_space_status_updated_at", table_name="memory_cards")
    op.drop_index(op.f("ix_memory_cards_user_id"), table_name="memory_cards")
    op.drop_index(op.f("ix_memory_cards_team_id"), table_name="memory_cards")
    op.drop_index(op.f("ix_memory_cards_status"), table_name="memory_cards")
    op.drop_index(op.f("ix_memory_cards_source_document_id"), table_name="memory_cards")
    op.drop_index(op.f("ix_memory_cards_space_id"), table_name="memory_cards")
    op.drop_table("memory_cards")
