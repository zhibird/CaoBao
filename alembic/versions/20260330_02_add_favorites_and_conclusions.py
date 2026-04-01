"""add answer favorites and conclusions

Revision ID: 20260330_02
Revises: 20260330_01
Create Date: 2026-03-30 13:20:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260330_02"
down_revision: Union[str, None] = "20260330_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "answer_favorites" not in table_names:
        op.create_table(
            "answer_favorites",
            sa.Column("favorite_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("space_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("conversation_id", sa.String(length=36), nullable=False),
            sa.Column("message_id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=128), nullable=False),
            sa.Column("question_text", sa.Text(), nullable=False),
            sa.Column("answer_text", sa.Text(), nullable=False),
            sa.Column("sources_json", sa.Text(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("tags_json", sa.Text(), nullable=True),
            sa.Column("is_promoted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.conversation_id"]),
            sa.ForeignKeyConstraint(["message_id"], ["chat_history.message_id"]),
            sa.ForeignKeyConstraint(["space_id"], ["project_spaces.space_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.PrimaryKeyConstraint("favorite_id"),
        )
    else:
        favorite_cols = {item["name"] for item in inspector.get_columns("answer_favorites")}
        if "is_promoted" not in favorite_cols:
            op.add_column(
                "answer_favorites",
                sa.Column("is_promoted", sa.Boolean(), nullable=False, server_default=sa.false()),
            )
        if "updated_at" not in favorite_cols:
            op.add_column(
                "answer_favorites",
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            )

    _ensure_index("answer_favorites", "ix_answer_favorites_conversation_id", ["conversation_id"])
    _ensure_index("answer_favorites", "ix_answer_favorites_is_promoted", ["is_promoted"])
    _ensure_index("answer_favorites", "ix_answer_favorites_message_id", ["message_id"])
    _ensure_index("answer_favorites", "ix_answer_favorites_space_id", ["space_id"])
    _ensure_index("answer_favorites", "ix_answer_favorites_team_id", ["team_id"])
    _ensure_index("answer_favorites", "ix_answer_favorites_user_id", ["user_id"])
    _ensure_index(
        "answer_favorites",
        "ix_answer_favorites_team_conversation_created_at",
        ["team_id", "conversation_id", "created_at"],
    )
    _ensure_index(
        "answer_favorites",
        "ix_answer_favorites_team_space_user_created_at",
        ["team_id", "space_id", "user_id", "created_at"],
    )

    if "conclusions" not in table_names:
        op.create_table(
            "conclusions",
            sa.Column("conclusion_id", sa.String(length=36), nullable=False),
            sa.Column("team_id", sa.String(length=64), nullable=False),
            sa.Column("space_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=128), nullable=False),
            sa.Column("topic", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
            sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("source_message_id", sa.String(length=36), nullable=True),
            sa.Column("source_favorite_id", sa.String(length=36), nullable=True),
            sa.Column("evidence_json", sa.Text(), nullable=True),
            sa.Column("tags_json", sa.Text(), nullable=True),
            sa.Column("doc_sync_document_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "status IN ('draft', 'confirmed', 'effective', 'superseded', 'archived')",
                name="ck_conclusions_status",
            ),
            sa.ForeignKeyConstraint(["doc_sync_document_id"], ["documents.document_id"]),
            sa.ForeignKeyConstraint(["source_favorite_id"], ["answer_favorites.favorite_id"]),
            sa.ForeignKeyConstraint(["source_message_id"], ["chat_history.message_id"]),
            sa.ForeignKeyConstraint(["space_id"], ["project_spaces.space_id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.PrimaryKeyConstraint("conclusion_id"),
        )
    else:
        conclusion_cols = {item["name"] for item in inspector.get_columns("conclusions")}
        if "updated_at" not in conclusion_cols:
            op.add_column(
                "conclusions",
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            )

    _ensure_index("conclusions", "ix_conclusions_doc_sync_document_id", ["doc_sync_document_id"])
    _ensure_index("conclusions", "ix_conclusions_source_favorite_id", ["source_favorite_id"])
    _ensure_index("conclusions", "ix_conclusions_source_message_id", ["source_message_id"])
    _ensure_index("conclusions", "ix_conclusions_space_id", ["space_id"])
    _ensure_index("conclusions", "ix_conclusions_status", ["status"])
    _ensure_index("conclusions", "ix_conclusions_team_id", ["team_id"])
    _ensure_index("conclusions", "ix_conclusions_user_id", ["user_id"])
    _ensure_index(
        "conclusions",
        "ix_conclusions_team_space_status_updated_at",
        ["team_id", "space_id", "status", "updated_at"],
    )
    _ensure_index(
        "conclusions",
        "ix_conclusions_team_topic_created_at",
        ["team_id", "topic", "created_at"],
    )


def _ensure_index(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in index_names:
        op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_conclusions_team_topic_created_at", table_name="conclusions")
    op.drop_index("ix_conclusions_team_space_status_updated_at", table_name="conclusions")
    op.drop_index(op.f("ix_conclusions_user_id"), table_name="conclusions")
    op.drop_index(op.f("ix_conclusions_team_id"), table_name="conclusions")
    op.drop_index(op.f("ix_conclusions_status"), table_name="conclusions")
    op.drop_index(op.f("ix_conclusions_space_id"), table_name="conclusions")
    op.drop_index(op.f("ix_conclusions_source_message_id"), table_name="conclusions")
    op.drop_index(op.f("ix_conclusions_source_favorite_id"), table_name="conclusions")
    op.drop_index(op.f("ix_conclusions_doc_sync_document_id"), table_name="conclusions")
    op.drop_table("conclusions")

    op.drop_index("ix_answer_favorites_team_space_user_created_at", table_name="answer_favorites")
    op.drop_index("ix_answer_favorites_team_conversation_created_at", table_name="answer_favorites")
    op.drop_index(op.f("ix_answer_favorites_user_id"), table_name="answer_favorites")
    op.drop_index(op.f("ix_answer_favorites_team_id"), table_name="answer_favorites")
    op.drop_index(op.f("ix_answer_favorites_space_id"), table_name="answer_favorites")
    op.drop_index(op.f("ix_answer_favorites_message_id"), table_name="answer_favorites")
    op.drop_index(op.f("ix_answer_favorites_is_promoted"), table_name="answer_favorites")
    op.drop_index(op.f("ix_answer_favorites_conversation_id"), table_name="answer_favorites")
    op.drop_table("answer_favorites")
