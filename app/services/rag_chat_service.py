from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.schemas.retrieval import RetrievalHit
from app.services.llm_model_service import LLMModelService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.user_service import UserService


class RagChatService:
    def __init__(
        self,
        user_service: UserService,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        llm_model_service: LLMModelService,
    ) -> None:
        self.user_service = user_service
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service
        self.llm_model_service = llm_model_service

    def ask(self, payload: ChatAskRequest) -> ChatAskResponse:
        self.user_service.ensure_user_in_team(
            user_id=payload.user_id,
            team_id=payload.team_id,
        )

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
        elif force_mock:
            selected_model = "none"
        elif requested_model:
            selected_model = requested_model
        else:
            selected_model = "default"

        should_use_rag = self.retrieval_service.has_indexed_chunks(
            team_id=payload.team_id,
            document_id=payload.document_id,
            conversation_id=payload.conversation_id,
        )

        if not should_use_rag:
            answer = self.llm_service.answer_chat(
                message=payload.question,
                model=selected_model,
                base_url=runtime_model.base_url if runtime_model is not None else None,
                api_key=runtime_model.api_key if runtime_model is not None else None,
                force_mock=force_mock,
            )
            return ChatAskResponse.from_result(
                user_id=payload.user_id,
                team_id=payload.team_id,
                conversation_id=payload.conversation_id,
                question=payload.question,
                answer=answer,
                hits=[],
                model=selected_model,
            )

        raw_hits = self.retrieval_service.search_chunks(
            team_id=payload.team_id,
            query=payload.question,
            top_k=payload.top_k,
            document_id=payload.document_id,
            conversation_id=payload.conversation_id,
            user_id=payload.user_id,
            embedding_model=payload.embedding_model,
        )

        answer = self.llm_service.answer_question(
            question=payload.question,
            hits=raw_hits,
            model=selected_model,
            base_url=runtime_model.base_url if runtime_model is not None else None,
            api_key=runtime_model.api_key if runtime_model is not None else None,
            force_mock=force_mock,
        )

        hits = [RetrievalHit.model_validate(item) for item in raw_hits]
        return ChatAskResponse.from_result(
            user_id=payload.user_id,
            team_id=payload.team_id,
            conversation_id=payload.conversation_id,
            question=payload.question,
            answer=answer,
            hits=hits,
            model=selected_model,
        )
