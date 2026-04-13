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


def test_settings_expose_auth_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///auth-config.db")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-auth-secret")

    settings = Settings(_env_file=None)

    assert settings.auth_jwt_secret == "test-auth-secret"
    assert settings.auth_jwt_algorithm == "HS256"
    assert settings.auth_access_token_ttl_minutes == 15
    assert settings.auth_refresh_token_ttl_days == 14
    assert settings.auth_access_cookie_name == "caibao_access_token"
    assert settings.auth_refresh_cookie_name == "caibao_refresh_token"
    assert settings.auth_cookie_samesite == "lax"
    assert settings.auth_cookie_secure is False


def test_blank_auth_cookie_domain_normalizes_to_none(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///auth-config.db")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-auth-secret")
    monkeypatch.setenv("AUTH_COOKIE_DOMAIN", "")

    settings = Settings(_env_file=None)

    assert settings.auth_cookie_domain is None
