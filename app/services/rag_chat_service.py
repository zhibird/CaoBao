from app.schemas.chat import ChatAskRequest, ChatAskResponse, ChatSource
from app.schemas.retrieval import RetrievalHit
from app.models.document import Document
from app.services.document_service import DocumentService
from app.services.llm_model_service import LLMModelService
from app.services.llm_service import LLMService, VisionAttachment
from app.services.retrieval_service import RetrievalService
from app.services.user_service import UserService


class RagChatService:
    def __init__(
        self,
        user_service: UserService,
        document_service: DocumentService,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        llm_model_service: LLMModelService,
    ) -> None:
        self.user_service = user_service
        self.document_service = document_service
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service
        self.llm_model_service = llm_model_service

    def ask(self, payload: ChatAskRequest) -> ChatAskResponse:
        self.user_service.ensure_user_in_team(
            user_id=payload.user_id,
            team_id=payload.team_id,
        )
        selected_document_ids = self._resolve_selected_document_ids(payload)
        scope_documents = self.document_service.get_documents_in_scope(
            team_id=payload.team_id,
            conversation_id=payload.conversation_id,
            document_ids=selected_document_ids,
            ready_only=True,
        )
        image_attachments = self._build_image_attachments(scope_documents)
        fallback_text_context = self._build_attachment_text_fallback(scope_documents)

        requested_model = payload.model.strip() if payload.model else None
        force_mock = False
        if requested_model and requested_model.lower() == "default":
            requested_model = None
        if requested_model and requested_model.lower() == "none":
            requested_model = None
            force_mock = True

        runtime_model = self.llm_model_service.resolve_runtime_config(
            team_id=payload.team_id,
            user_id=payload.user_id,
            model_name=requested_model,
        )
        if runtime_model is not None:
            selected_model = runtime_model.model_name
            runtime_selected_model = runtime_model.model_name
        elif force_mock:
            selected_model = "none"
            runtime_selected_model = None
        elif requested_model:
            selected_model = requested_model
            runtime_selected_model = requested_model
        else:
            selected_model = "default"
            runtime_selected_model = None

        should_use_rag = self.retrieval_service.has_indexed_chunks(
            team_id=payload.team_id,
            document_id=payload.document_id,
            document_ids=selected_document_ids,
            conversation_id=payload.conversation_id,
        )

        if not should_use_rag:
            answer = self.llm_service.answer_chat(
                message=payload.question,
                model=runtime_selected_model,
                base_url=runtime_model.base_url if runtime_model is not None else None,
                api_key=runtime_model.api_key if runtime_model is not None else None,
                force_mock=force_mock,
                image_attachments=image_attachments,
                fallback_text_context=fallback_text_context,
            )
            return ChatAskResponse.from_result(
                user_id=payload.user_id,
                team_id=payload.team_id,
                conversation_id=payload.conversation_id,
                question=payload.question,
                answer=answer,
                hits=[],
                mode="chat",
                sources=[],
                model=selected_model,
            )

        raw_hits = self.retrieval_service.search_chunks(
            team_id=payload.team_id,
            query=payload.question,
            top_k=payload.top_k,
            document_id=payload.document_id,
            document_ids=selected_document_ids,
            conversation_id=payload.conversation_id,
            user_id=payload.user_id,
            embedding_model=payload.embedding_model,
        )

        answer = self.llm_service.answer_question(
            question=payload.question,
            hits=raw_hits,
            model=runtime_selected_model,
            base_url=runtime_model.base_url if runtime_model is not None else None,
            api_key=runtime_model.api_key if runtime_model is not None else None,
            force_mock=force_mock,
            image_attachments=image_attachments,
        )

        hits = [RetrievalHit.model_validate(item) for item in raw_hits]
        sources = self._build_sources(raw_hits)
        return ChatAskResponse.from_result(
            user_id=payload.user_id,
            team_id=payload.team_id,
            conversation_id=payload.conversation_id,
            question=payload.question,
            answer=answer,
            hits=hits,
            mode="rag",
            sources=sources,
            model=selected_model,
        )

    def _build_sources(self, raw_hits: list[dict[str, object]]) -> list[ChatSource]:
        seen: set[str] = set()
        sources: list[ChatSource] = []
        for hit in raw_hits:
            chunk_id = str(hit.get("chunk_id", "")).strip()
            if not chunk_id or chunk_id in seen:
                continue
            seen.add(chunk_id)
            sources.append(
                ChatSource(
                    document_id=str(hit.get("document_id", "")),
                    source_name=(str(hit.get("source_name", "")).strip() or None),
                    chunk_id=chunk_id,
                    chunk_index=int(hit.get("chunk_index", 0)),
                    page_no=int(hit.get("page_no")) if hit.get("page_no") is not None else None,
                    locator_label=(str(hit.get("locator_label", "")).strip() or None),
                    snippet=self._build_snippet(hit.get("content")),
                    score=float(hit.get("score", 0.0)),
                )
            )
        return sources

    def _build_image_attachments(self, documents: list[Document]) -> list[VisionAttachment]:
        raw_items = self.document_service.build_chat_image_attachments(documents=documents)
        attachments: list[VisionAttachment] = []
        for item in raw_items:
            data_url = str(item.get("data_url", "")).strip()
            if not data_url:
                continue
            attachments.append(
                VisionAttachment(
                    document_id=str(item.get("document_id", "")).strip(),
                    source_name=str(item.get("source_name", "")).strip(),
                    mime_type=str(item.get("mime_type", "")).strip(),
                    data_url=data_url,
                )
            )
        return attachments

    def _build_attachment_text_fallback(self, documents: list[Document]) -> str | None:
        parts: list[str] = []
        for item in documents:
            content_type = str(getattr(item, "content_type", "")).strip().lower()
            if content_type not in {"png", "jpg", "jpeg", "webp"}:
                continue
            source_name = str(getattr(item, "source_name", "")).strip() or "image"
            content = str(getattr(item, "content", "")).strip()
            if not content:
                continue
            parts.append(f"[{source_name}]\n{content}")
        if not parts:
            return None
        return "\n\n".join(parts)

    def _resolve_selected_document_ids(self, payload: ChatAskRequest) -> list[str] | None:
        values: list[str] = []
        if payload.document_id:
            values.append(payload.document_id)
        if payload.selected_document_ids:
            values.extend(payload.selected_document_ids)

        deduped: list[str] = []
        for item in values:
            normalized = str(item).strip()
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped or None

    def _build_snippet(self, raw_content: object) -> str | None:
        if not isinstance(raw_content, str):
            return None
        text = " ".join(raw_content.split())
        if not text:
            return None
        return text[:220]
