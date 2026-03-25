from __future__ import annotations

from dataclasses import dataclass
import re

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import DomainValidationError


@dataclass(frozen=True)
class VisionAttachment:
    document_id: str
    source_name: str
    mime_type: str
    data_url: str


class LLMService:
    """LLM wrapper with a default local mock mode for beginner-friendly setup."""
    _CONTINUE_PROMPT = "Continue exactly from where you stopped. Do not repeat prior text. Finish the current answer."
    _MAX_COMPLETION_SEGMENTS = 4

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
        image_attachments: list[VisionAttachment] | None = None,
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
            image_attachments=image_attachments,
        )

    def answer_chat(
        self,
        message: str,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        force_mock: bool = False,
        image_attachments: list[VisionAttachment] | None = None,
        fallback_text_context: str | None = None,
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
            image_attachments=image_attachments,
            fallback_text_context=fallback_text_context,
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
        image_attachments: list[VisionAttachment] | None = None,
    ) -> str:
        context = self._build_context(hits)

        system_prompt = (
            "You are CaiBao, an enterprise assistant. Answer strictly based on the provided context. "
            "If context is insufficient, say so explicitly."
        )
        if image_attachments:
            system_prompt += " Attached images are primary evidence when relevant. Use context as supporting material."
        user_prompt = f"Question:\n{question}\n\nContext:\n{context}"

        try:
            return self._request_chat_answer(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                base_url=base_url,
                api_key=api_key,
                image_attachments=image_attachments,
            )
        except DomainValidationError as exc:
            if image_attachments and self._should_retry_without_images(str(exc)):
                return self._request_chat_answer(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    base_url=base_url,
                    api_key=api_key,
                    image_attachments=None,
                )
            raise

    def _openai_compatible_chat_answer(
        self,
        message: str,
        model: str | None = None,
        base_url: str = "",
        api_key: str = "",
        image_attachments: list[VisionAttachment] | None = None,
        fallback_text_context: str | None = None,
    ) -> str:
        system_prompt = "You are CaiBao, a helpful enterprise assistant."
        try:
            return self._request_chat_answer(
                model=model,
                system_prompt=system_prompt,
                user_prompt=message,
                base_url=base_url,
                api_key=api_key,
                image_attachments=image_attachments,
            )
        except DomainValidationError as exc:
            if image_attachments and self._should_retry_without_images(str(exc)):
                fallback_prompt = self._build_fallback_chat_prompt(
                    message=message,
                    fallback_text_context=fallback_text_context,
                )
                return self._request_chat_answer(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=fallback_prompt,
                    base_url=base_url,
                    api_key=api_key,
                    image_attachments=None,
                )
            raise

    def _build_payload(self, model: str | None, messages: list[dict[str, object]]) -> dict[str, object]:
        selected_model = model.strip() if model else self.settings.llm_model
        return {
            "model": selected_model,
            "messages": messages,
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
        }

    def _request_chat_answer(
        self,
        *,
        model: str | None,
        system_prompt: str,
        user_prompt: str,
        base_url: str,
        api_key: str,
        image_attachments: list[VisionAttachment] | None,
    ) -> str:
        user_content = self._build_user_content(
            user_prompt=user_prompt,
            image_attachments=image_attachments,
        )
        messages: list[dict[str, object]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        answer_parts: list[str] = []

        for _ in range(self._MAX_COMPLETION_SEGMENTS):
            payload = self._build_payload(model=model, messages=messages)
            try:
                response = self._post_chat_completion(
                    payload=payload,
                    base_url=base_url,
                    api_key=api_key,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = self._extract_http_error_detail(exc.response)
                raise DomainValidationError(f"LLM request failed: {detail}") from exc
            except httpx.HTTPError as exc:
                raise DomainValidationError(f"LLM request failed: {exc}") from exc

            body = response.json()
            answer_part, finish_reason = self._parse_llm_answer(body)
            answer_parts.append(answer_part)

            if finish_reason != "length":
                break

            messages.append({"role": "assistant", "content": answer_part})
            messages.append({"role": "user", "content": self._CONTINUE_PROMPT})

        answer = "".join(answer_parts).strip()
        if not answer:
            raise DomainValidationError("LLM returned an empty answer.")
        return answer

    def _build_user_content(
        self,
        *,
        user_prompt: str,
        image_attachments: list[VisionAttachment] | None,
    ) -> str | list[dict[str, object]]:
        if not image_attachments:
            return user_prompt

        content: list[dict[str, object]] = [{"type": "text", "text": user_prompt}]
        for item in image_attachments:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": item.data_url,
                        "detail": "auto",
                    },
                }
            )
        return content

    def _build_fallback_chat_prompt(self, *, message: str, fallback_text_context: str | None) -> str:
        normalized_context = (fallback_text_context or "").strip()
        if not normalized_context:
            return message
        return f"{message}\n\nAttachment text fallback:\n{normalized_context}"

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
        settings_base_url = self.settings.llm_base_url.strip()
        settings_key = (self.settings.llm_api_key or "").strip()

        if provider == "mock":
            # Compat: if user filled .env base_url + api_key but forgot to switch provider,
            # treat default runtime as real provider instead of forcing mock.
            if settings_base_url and settings_key:
                return settings_base_url, settings_key
            return None

        if not settings_key:
            raise DomainValidationError("LLM_API_KEY is required when llm_provider is not 'mock'.")
        return settings_base_url, settings_key

    def _extract_http_error_detail(self, response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            body = None

        if isinstance(body, dict):
            detail = body.get("error") or body.get("detail") or body.get("message")
            if isinstance(detail, dict):
                message = detail.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()
            if isinstance(detail, str) and detail.strip():
                return detail.strip()

        text = response.text.strip()
        if text:
            return text
        return f"HTTP {response.status_code}"

    def _should_retry_without_images(self, error_message: str) -> bool:
        normalized = error_message.lower()
        keywords = [
            "image",
            "vision",
            "multimodal",
            "does not support",
            "unsupported content",
            "invalid content type",
            "content type",
            "input_image",
            "image_url",
        ]
        return any(keyword in normalized for keyword in keywords)

    def _parse_llm_answer(self, body: dict[str, object]) -> tuple[str, str | None]:
        try:
            choice = body["choices"][0]  # type: ignore[index]
            content = choice["message"]["content"]  # type: ignore[index]
        except (KeyError, IndexError, TypeError) as exc:
            raise DomainValidationError("LLM response format is invalid.") from exc

        answer = self._extract_message_content(content)
        if not answer.strip():
            raise DomainValidationError("LLM returned an empty answer.")
        finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
        return answer, str(finish_reason).strip() if finish_reason is not None else None

    def _extract_message_content(self, content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                    continue
                if item.get("type") == "text":
                    inner_text = item.get("text")
                    if isinstance(inner_text, str):
                        parts.append(inner_text)
            return "".join(parts)
        return str(content)

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
