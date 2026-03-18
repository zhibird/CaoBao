from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.schemas.retrieval import RetrievalHit
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.user_service import UserService


class RagChatService:
    def __init__(
        self,
        user_service: UserService,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
    ) -> None:
        self.user_service = user_service
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service

    def ask(self, payload: ChatAskRequest) -> ChatAskResponse:
        self.user_service.ensure_user_in_team(
            user_id=payload.user_id,
            team_id=payload.team_id,
        )

        raw_hits = self.retrieval_service.search_chunks(
            team_id=payload.team_id,
            query=payload.question,
            top_k=payload.top_k,
            document_id=payload.document_id,
        )

        answer = self.llm_service.answer_question(
            question=payload.question,
            hits=raw_hits,
            model=payload.model,
        )

        hits = [RetrievalHit.model_validate(item) for item in raw_hits]
        return ChatAskResponse.from_result(
            user_id=payload.user_id,
            team_id=payload.team_id,
            question=payload.question,
            answer=answer,
            hits=hits,
            model=payload.model,
        )
