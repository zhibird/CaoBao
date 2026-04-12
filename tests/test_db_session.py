import pytest

from app.db.session import _is_sqlite_url
from app.db.session import _should_run_legacy_init


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("sqlite:///./local.db", True),
        ("sqlite+pysqlite:///./local.db", True),
        ("postgresql+psycopg://user:pass@localhost:5432/caibao", False),
        ("postgres://user:pass@localhost:5432/caibao", False),
        ("mysql+pymysql://user:pass@localhost:3306/caibao", False),
    ],
)
def test_is_sqlite_url_recognizes_only_sqlite_urls(database_url: str, expected: bool):
    assert _is_sqlite_url(database_url) is expected


def test_legacy_init_cannot_be_enabled_for_postgresql():
    with pytest.raises(RuntimeError, match="Legacy DB bootstrap is forbidden for non-SQLite databases"):
        _should_run_legacy_init(
            database_url="postgresql+psycopg://user:pass@localhost:5432/caibao",
            app_env="dev",
            explicit=True,
        )


def test_legacy_init_defaults_to_false_in_prod():
    assert (
        _should_run_legacy_init(
            database_url="sqlite:///./local.db",
            app_env="prod",
            explicit=None,
        )
        is False
    )


def test_legacy_init_defaults_to_false_for_postgresql_in_dev():
    assert (
        _should_run_legacy_init(
            database_url="postgresql+psycopg://user:pass@localhost:5432/caibao",
            app_env="dev",
            explicit=None,
        )
        is False
    )
