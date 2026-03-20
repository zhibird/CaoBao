from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import DomainValidationError
from app.services.embedding_service import EmbeddingService


class _FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict[str, object]:
        return self._body


def test_embedding_service_mock_vectors() -> None:
    settings = Settings(embedding_provider="mock", embedding_mock_dim=32)
    service = EmbeddingService(settings=settings)

    vectors = service.embed_texts(["hello world", "hello retrieval"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 32
    assert len(vectors[1]) == 32
    assert service.model_name == "hashing_v1"


def test_embedding_service_real_provider_calls_api(monkeypatch) -> None:
    captured_payload: dict[str, object] = {}

    def _fake_post(url, headers, json, timeout):  # noqa: ANN001
        captured_payload["url"] = url
        captured_payload["headers"] = headers
        captured_payload["json"] = json
        captured_payload["timeout"] = timeout
        return _FakeResponse(
            {
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                    {"index": 1, "embedding": [0.3, 0.2, 0.1]},
                ]
            }
        )

    monkeypatch.setattr("app.services.embedding_service.httpx.post", _fake_post)

    settings = Settings(
        embedding_provider="openai",
        embedding_base_url="https://api.openai.com/v1",
        embedding_api_key="sk-test",
        embedding_model="text-embedding-3-small",
        embedding_timeout_seconds=5.0,
    )
    service = EmbeddingService(settings=settings)

    vectors = service.embed_texts(["alpha", "beta"])
    assert vectors == [[0.1, 0.2, 0.3], [0.3, 0.2, 0.1]]
    assert captured_payload["url"] == "https://api.openai.com/v1/embeddings"
    assert captured_payload["json"] == {
        "model": "text-embedding-3-small",
        "input": ["alpha", "beta"],
    }
    assert service.model_name == "text-embedding-3-small"
    assert service.dim == 3


def test_embedding_service_real_provider_requires_api_key() -> None:
    settings = Settings(
        embedding_provider="openai",
        embedding_base_url="https://api.openai.com/v1",
        embedding_api_key=None,
    )
    service = EmbeddingService(settings=settings)

    try:
        service.embed_texts(["alpha"])
    except DomainValidationError as exc:
        assert "EMBEDDING_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected DomainValidationError for missing EMBEDDING_API_KEY.")
