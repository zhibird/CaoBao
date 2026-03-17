import hashlib
import math
import re


class EmbeddingService:
    """Deterministic local embedding for MVP retrieval.

    Uses feature hashing to avoid external model dependencies in early stages.
    """

    def __init__(self, dim: int = 256, model_name: str = "hashing_v1") -> None:
        self.dim = dim
        self.model_name = model_name

    def embed_text(self, text: str) -> list[float]:
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

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0

        return float(sum(x * y for x, y in zip(a, b)))

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())