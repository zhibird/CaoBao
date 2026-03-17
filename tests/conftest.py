from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
