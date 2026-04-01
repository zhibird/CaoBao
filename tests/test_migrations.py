from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from app.db.base import Base
from app.models import *  # noqa: F401,F403


def _make_alembic_config(db_file: Path) -> Config:
    config = Config(str(Path("alembic.ini").resolve()))
    config.set_main_option("script_location", str(Path("alembic").resolve()))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_file.as_posix()}")
    return config


def _current_revision(db_file: Path) -> str | None:
    if not db_file.exists():
        return None
    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ).fetchone()
        if row is None:
            return None
        revision = conn.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
        if revision is None:
            return None
        return str(revision[0]).strip() or None


def test_migration_fresh_database_upgrade_head(tmp_path) -> None:
    db_file = tmp_path / "fresh.db"
    config = _make_alembic_config(db_file)

    command.upgrade(config, "head")

    assert _current_revision(db_file) == "20260330_02"
    with sqlite3.connect(db_file) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    assert {"teams", "users", "project_spaces", "memory_cards", "answer_favorites", "conclusions"} <= tables


def test_migration_legacy_database_stamp_then_upgrade(tmp_path) -> None:
    db_file = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    config = _make_alembic_config(db_file)
    command.stamp(config, "20260330_02")
    command.upgrade(config, "head")

    assert _current_revision(db_file) == "20260330_02"


def test_migration_upgrade_from_half_upgraded_database(tmp_path) -> None:
    db_file = tmp_path / "half.db"
    config = _make_alembic_config(db_file)

    command.upgrade(config, "20260330_00")
    assert _current_revision(db_file) == "20260330_00"

    command.upgrade(config, "head")
    assert _current_revision(db_file) == "20260330_02"
