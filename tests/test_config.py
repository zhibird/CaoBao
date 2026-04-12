import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_UPLOAD_ROOT_DIR, Settings


def test_settings_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_upload_root_dir_defaults_with_postgres_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/caibao")
    monkeypatch.delenv("UPLOAD_ROOT_DIR", raising=False)

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://user:pass@localhost:5432/caibao"
    assert settings.upload_root_dir == DEFAULT_UPLOAD_ROOT_DIR
