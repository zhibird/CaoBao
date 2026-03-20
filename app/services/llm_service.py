from __future__ import annotations

import re

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import DomainValidationError


class LLMService:
    """LLM wrapper with a default local mock mode for beginner-friendly setup."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def answer_question(
        self,
        question: str,
        hits: list[dict[str, object]],
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        force_mock: bool = False,
    ) -> str:
        if force_mock:
            return self._mock_answer(question=question, hits=hits)

        runtime = self._resolve_runtime(base_url=base_url, api_key=api_key)
        if runtime is None:
            return self._mock_answer(question=question, hits=hits)

        return self._openai_compatible_answer(
            question=question,
            hits=hits,
            model=model,
            base_url=runtime[0],
            api_key=runtime[1],
        )

    def answer_chat(
        self,
        message: str,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        force_mock: bool = False,
    ) -> str:
        """General chat answer without retrieval context."""
        if force_mock:
            return self._mock_chat_answer(message=message)

        runtime = self._resolve_runtime(base_url=base_url, api_key=api_key)
        if runtime is None:
            return self._mock_chat_answer(message=message)

        return self._openai_compatible_chat_answer(
            message=message,
            model=model,
            base_url=runtime[0],
            api_key=runtime[1],
        )

    def _mock_answer(self, question: str, hits: list[dict[str, object]]) -> str:
        if not hits:
            return "No relevant knowledge chunks were found, so I cannot answer this yet."

        candidates = self._extract_candidate_sentences(hits)
        if not candidates:
            return "Chunks were retrieved, but their content is empty, so no answer can be generated."

        answer = self._pick_best_sentence(question=question, candidates=candidates)
        return f"[Mock Answer] {answer}"

    def _mock_chat_answer(self, message: str) -> str:
        normalized = message.strip()
        if not normalized:
            return "[Mock Chat] Please tell me what you want to discuss."
        return f"[Mock Chat] {normalized}"

    def _openai_compatible_answer(
        self,
        question: str,
        hits: list[dict[str, object]],
        model: str | None = None,
        base_url: str = "",
        api_key: str = "",
    ) -> str:
        context = self._build_context(hits)

        system_prompt = (
            "You are CaiBao, an enterprise assistant. Answer strictly based on the provided context. "
            "If context is insufficient, say so explicitly."
        )
        user_prompt = f"Question:\n{question}\n\nContext:\n{context}"

        payload = self._build_payload(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        try:
            response = self._post_chat_completion(
                payload=payload,
                base_url=base_url,
                api_key=api_key,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DomainValidationError(f"LLM request failed: {exc}") from exc

        return self._parse_llm_answer(response.json())

    def _openai_compatible_chat_answer(
        self,
        message: str,
        model: str | None = None,
        base_url: str = "",
        api_key: str = "",
    ) -> str:
        system_prompt = "You are CaiBao, a helpful enterprise assistant."
        payload = self._build_payload(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
        )

        try:
            response = self._post_chat_completion(
                payload=payload,
                base_url=base_url,
                api_key=api_key,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DomainValidationError(f"LLM request failed: {exc}") from exc

        return self._parse_llm_answer(response.json())

    def _build_payload(self, model: str | None, messages: list[dict[str, str]]) -> dict[str, object]:
        selected_model = model.strip() if model else self.settings.llm_model
        return {
            "model": selected_model,
            "messages": messages,
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
        }

    def _post_chat_completion(
        self,
        payload: dict[str, object],
        *,
        base_url: str,
        api_key: str,
    ) -> httpx.Response:
        normalized_base_url = base_url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        return httpx.post(
            f"{normalized_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.settings.llm_timeout_seconds,
        )

    def _resolve_runtime(self, *, base_url: str | None, api_key: str | None) -> tuple[str, str] | None:
        runtime_base_url = (base_url or "").strip()
        runtime_api_key = (api_key or "").strip()
        if runtime_base_url or runtime_api_key:
            if not runtime_base_url or not runtime_api_key:
                raise DomainValidationError("Both base_url and api_key are required for custom model.")
            return runtime_base_url, runtime_api_key

        provider = self.settings.llm_provider.lower().strip()
        if provider == "mock":
            return None

        settings_key = (self.settings.llm_api_key or "").strip()
        if not settings_key:
            raise DomainValidationError("LLM_API_KEY is required when llm_provider is not 'mock'.")
        return self.settings.llm_base_url, settings_key

    def _parse_llm_answer(self, body: dict[str, object]) -> str:
        try:
            content = body["choices"][0]["message"]["content"]  # type: ignore[index]
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
