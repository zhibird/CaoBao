import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.engine import make_url


def _make_alembic_config(database_url: str) -> Config:
    config = Config(str(Path("alembic.ini").resolve()))
    config.set_main_option("script_location", str(Path("alembic").resolve()))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _resolve_test_database_url() -> str:
    configured_url = os.environ.get("TEST_DATABASE_URL")
    if configured_url:
        return configured_url

    test_db_path = (Path(".pytest_cache") / f"caibao_test_{uuid4().hex}.db").resolve()
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{test_db_path.as_posix()}"


TEST_DATABASE_URL = _resolve_test_database_url()
TEST_DATABASE_BACKEND = make_url(TEST_DATABASE_URL).get_backend_name()

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DB_LEGACY_INIT_ENABLED"] = "true" if TEST_DATABASE_BACKEND == "sqlite" else "false"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["LLM_API_KEY"] = ""
os.environ["EMBEDDING_API_KEY"] = ""
os.environ["DEV_ADMIN_ENABLED"] = "true"
os.environ["DEV_ADMIN_ACCOUNT_ID"] = "dev_admin_test"
os.environ["DEV_ADMIN_DISPLAY_NAME"] = "Developer Admin Test"
os.environ["DEV_ADMIN_TOKEN"] = "test-admin-token"

from app.core.config import reload_settings

reload_settings()

if TEST_DATABASE_BACKEND != "sqlite":
    command.upgrade(_make_alembic_config(TEST_DATABASE_URL), "head")

from app.main import create_app


@pytest.fixture(scope="session")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
