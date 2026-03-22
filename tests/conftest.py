import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

# Keep tests deterministic and independent from local/production .env values.
TEST_DB_PATH = Path(".pytest_cache") / "caibao_test.db"
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
TEST_DB_PATH = TEST_DB_PATH.with_name(f"caibao_test_{uuid4().hex}.db")

os.environ["DATABASE_URL"] = "sqlite:///./.pytest_cache/caibao_test.db"
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

from app.main import create_app


@pytest.fixture(scope="session")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
