"""add standard auth persistence schema

Revision ID: 20260412_00
Revises: 20260330_02
Create Date: 2026-04-12 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260412_00"
down_revision: Union[str, None] = "20260330_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "users" in table_names:
        user_columns = {item["name"] for item in inspector.get_columns("users")}
        if "password_hash" not in user_columns:
            op.add_column(
                "users",
                sa.Column("password_hash", sa.String(length=255), nullable=True),
            )
        if "is_active" not in user_columns:
            op.add_column(
                "users",
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            )
        if "password_updated_at" not in user_columns:
            op.add_column(
                "users",
                sa.Column("password_updated_at", sa.DateTime(timezone=True), nullable=True),
            )

    if "auth_refresh_sessions" not in table_names:
        op.create_table(
            "auth_refresh_sessions",
            sa.Column("session_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("replaced_by_session_id", sa.String(length=36), nullable=True),
            sa.Column("user_agent", sa.String(length=500), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
            sa.PrimaryKeyConstraint("session_id"),
        )

    _ensure_index("auth_refresh_sessions", "ix_auth_refresh_sessions_user_id", ["user_id"])
    _ensure_index(
        "auth_refresh_sessions",
        "ix_auth_refresh_sessions_refresh_token_hash",
        ["refresh_token_hash"],
    )


def _ensure_index(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in set(inspector.get_table_names()):
        return
    index_names = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in index_names:
        op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_refresh_sessions_refresh_token_hash", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_user_id", table_name="auth_refresh_sessions")
    op.drop_table("auth_refresh_sessions")
    op.drop_column("users", "password_updated_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "password_hash")
