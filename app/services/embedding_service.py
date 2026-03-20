from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import DomainValidationError


@dataclass(slots=True)
class EmbeddingRuntimeConfig:
    provider: str
    model_name: str
    base_url: str | None = None
    api_key: str | None = None

    @classmethod
    def mock_default(cls, model_name: str = "hashing_v1") -> "EmbeddingRuntimeConfig":
        return cls(
            provider="mock",
            model_name=model_name,
            base_url=None,
            api_key=None,
        )


class EmbeddingService:
    """Embedding wrapper with mock + real provider modes."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.provider = self.settings.embedding_provider.strip().lower()
        self.batch_size = max(1, self.settings.embedding_batch_size)

        if self.provider == "mock":
            self.dim = max(8, self.settings.embedding_mock_dim)
            self.model_name = "hashing_v1"
        else:
            self.dim = 0
            self.model_name = self.settings.embedding_model

    def embed_text(self, text: str, runtime: EmbeddingRuntimeConfig | None = None) -> list[float]:
        vectors = self.embed_texts([text], runtime=runtime)
        return vectors[0]

    def embed_texts(
        self,
        texts: list[str],
        runtime: EmbeddingRuntimeConfig | None = None,
    ) -> list[list[float]]:
        normalized_texts = [str(text) for text in texts]
        if not normalized_texts:
            return []

        runtime_provider, runtime_model_name, runtime_base_url, runtime_api_key = self._resolve_runtime(runtime)
        self.provider = runtime_provider

        if runtime_provider == "mock":
            self.dim = max(8, self.settings.embedding_mock_dim)
            self.model_name = runtime_model_name or "hashing_v1"
            vectors = [self._mock_embed_text(text) for text in normalized_texts]
            self.dim = len(vectors[0]) if vectors else self.dim
            return vectors

        base_url = self._normalize_base_url(runtime_base_url or "")
        api_key = (runtime_api_key or "").strip()
        if not api_key:
            raise DomainValidationError(
                "EMBEDDING_API_KEY is required when embedding_provider is not 'mock'."
            )

        payload = {
            "model": runtime_model_name,
            "input": normalized_texts,
        }
        url = f"{base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.settings.embedding_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DomainValidationError(f"Embedding request failed: {exc}") from exc

        vectors = self._parse_embeddings_response(response.json(), expected_size=len(normalized_texts))
        if vectors:
            self.dim = len(vectors[0])
        self.model_name = runtime_model_name
        return vectors

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0

        return float(sum(x * y for x, y in zip(a, b)))

    def _mock_embed_text(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dim

        vector = [0.0] * self.dim
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]

    def _parse_embeddings_response(
        self,
        body: dict[str, object],
        *,
        expected_size: int,
    ) -> list[list[float]]:
        data = body.get("data")
        if not isinstance(data, list):
            raise DomainValidationError("Embedding response format is invalid: missing data.")

        parsed_rows: list[tuple[int, list[float]]] = []
        for row in data:
            if not isinstance(row, dict):
                raise DomainValidationError("Embedding response format is invalid: row is not object.")

            index = row.get("index")
            embedding = row.get("embedding")
            if not isinstance(index, int) or not isinstance(embedding, list):
                raise DomainValidationError("Embedding response format is invalid: missing index/embedding.")

            vector: list[float] = []
            for value in embedding:
                if not isinstance(value, (int, float)):
                    raise DomainValidationError("Embedding response format is invalid: non-numeric vector value.")
                vector.append(float(value))

            parsed_rows.append((index, vector))

        if len(parsed_rows) != expected_size:
            raise DomainValidationError(
                f"Embedding response count mismatch: expected {expected_size}, got {len(parsed_rows)}."
            )

        parsed_rows.sort(key=lambda item: item[0])
        ordered = [item[1] for item in parsed_rows]

        first_dim = len(ordered[0]) if ordered else 0
        if first_dim <= 0:
            raise DomainValidationError("Embedding response contains empty vectors.")
        if any(len(vector) != first_dim for vector in ordered):
            raise DomainValidationError("Embedding response vectors have inconsistent dimensions.")

        return ordered

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def _resolve_runtime(
        self,
        runtime: EmbeddingRuntimeConfig | None,
    ) -> tuple[str, str, str | None, str | None]:
        if runtime is None:
            provider = self.settings.embedding_provider.strip().lower()
            if provider == "mock":
                return "mock", "hashing_v1", None, None
            return (
                provider,
                self.settings.embedding_model,
                self.settings.embedding_base_url,
                self.settings.embedding_api_key,
            )

        provider = runtime.provider.strip().lower()
        model_name = runtime.model_name.strip()
        if not provider:
            raise DomainValidationError("embedding runtime provider cannot be empty.")
        if provider == "mock":
            return "mock", model_name or "hashing_v1", None, None
        if not model_name:
            raise DomainValidationError("embedding runtime model_name cannot be empty.")
        return provider, model_name, runtime.base_url, runtime.api_key

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        value = raw.strip().rstrip("/")
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DomainValidationError("embedding_base_url must be a valid http(s) URL.")
        return value
