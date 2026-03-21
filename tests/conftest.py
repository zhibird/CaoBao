import os

from fastapi.testclient import TestClient
import pytest

from app.core.config import reload_settings
from app.main import create_app

# Keep tests deterministic and independent from local/production .env values.
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["LLM_API_KEY"] = ""
os.environ["EMBEDDING_API_KEY"] = ""
os.environ["DEV_ADMIN_ENABLED"] = "true"
os.environ["DEV_ADMIN_ACCOUNT_ID"] = "dev_admin_test"
os.environ["DEV_ADMIN_DISPLAY_NAME"] = "Developer Admin Test"
os.environ["DEV_ADMIN_TOKEN"] = "test-admin-token"
reload_settings()


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
