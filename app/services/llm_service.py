from __future__ import annotations

import re

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import DomainValidationError


class LLMService:
    """LLM wrapper with a default local mock mode for beginner-friendly setup."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def answer_question(self, question: str, hits: list[dict[str, object]]) -> str:
        provider = self.settings.llm_provider.lower().strip()
        if provider == "mock":
            return self._mock_answer(question=question, hits=hits)

        return self._openai_compatible_answer(question=question, hits=hits)

    def _mock_answer(self, question: str, hits: list[dict[str, object]]) -> str:
        if not hits:
            return "No relevant knowledge chunks were found, so I cannot answer this yet."

        candidates = self._extract_candidate_sentences(hits)
        if not candidates:
            return "Chunks were retrieved, but their content is empty, so no answer can be generated."

        answer = self._pick_best_sentence(question=question, candidates=candidates)
        return f"[Mock Answer] {answer}"

    def _openai_compatible_answer(self, question: str, hits: list[dict[str, object]]) -> str:
        if not self.settings.llm_api_key:
            raise DomainValidationError("LLM_API_KEY is required when llm_provider is not 'mock'.")

        context = self._build_context(hits)

        system_prompt = (
            "You are CaiBao, an enterprise assistant. Answer strictly based on the provided context. "
            "If context is insufficient, say so explicitly."
        )
        user_prompt = f"Question:\n{question}\n\nContext:\n{context}"

        base_url = self.settings.llm_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
        }

        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DomainValidationError(f"LLM request failed: {exc}") from exc

        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DomainValidationError("LLM response format is invalid.") from exc

        answer = str(content).strip()
        if not answer:
            raise DomainValidationError("LLM returned an empty answer.")

        return answer

    def _build_context(self, hits: list[dict[str, object]]) -> str:
        if not hits:
            return "(no context)"

        lines: list[str] = []
        for idx, hit in enumerate(hits, start=1):
            doc_id = str(hit.get("document_id", ""))
            chunk_index = hit.get("chunk_index", "")
            content = str(hit.get("content", "")).strip()
            lines.append(f"[{idx}] doc={doc_id} chunk={chunk_index}: {content}")

        return "\n".join(lines)

    def _extract_candidate_sentences(self, hits: list[dict[str, object]]) -> list[str]:
        candidates: list[str] = []
        for hit in hits[:3]:
            raw = str(hit.get("content", "")).strip()
            if not raw:
                continue

            cleaned = re.sub(r"(?m)^#+\s*.*$", " ", raw)
            normalized = re.sub(r"\s+", " ", cleaned)
            parts = re.split(r"(?<=[.!?])\s+", normalized)
            for part in parts:
                sentence = part.strip(" -\t\r\n")
                if sentence:
                    candidates.append(sentence[:200])
        return candidates

    def _pick_best_sentence(self, question: str, candidates: list[str]) -> str:
        if not candidates:
            return ""

        q_tokens = set(re.findall(r"\w+", question.lower()))
        if not q_tokens:
            return candidates[0]

        best_sentence = candidates[0]
        best_score = -1
        for sentence in candidates:
            s_tokens = set(re.findall(r"\w+", sentence.lower()))
            score = len(q_tokens.intersection(s_tokens))
            if score > best_score:
                best_score = score
                best_sentence = sentence

        return best_sentence
