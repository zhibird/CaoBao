from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_action_chat_service,
    get_chat_history_service,
    get_chat_service,
    get_rag_chat_service,
)
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.schemas.chat import (
    ChatActionRequest,
    ChatActionResponse,
    ChatAskRequest,
    ChatAskResponse,
    ChatEchoRequest,
    ChatEchoResponse,
    ChatHistoryItem,
    ChatHistoryListResponse,
)
from app.services.action_chat_service import ActionChatService
from app.services.chat_history_service import ChatHistoryService
from app.services.chat_service import ChatService
from app.services.rag_chat_service import RagChatService

router = APIRouter(prefix="/chat")


@router.post("/echo", response_model=ChatEchoResponse)
def chat_echo(
    payload: ChatEchoRequest,
    chat_service: ChatService = Depends(get_chat_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatEchoResponse:
    try:
        response = chat_service.echo(payload)
        chat_history_service.record_message(
            team_id=payload.team_id,
            user_id=payload.user_id,
            conversation_id=payload.conversation_id,
            channel="echo",
            request_text=payload.message,
            response_text=response.answer,
            request_payload=payload.model_dump(),
            response_payload=response.model_dump(),
        )
        return response
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/ask", response_model=ChatAskResponse)
def chat_ask(
    payload: ChatAskRequest,
    rag_chat_service: RagChatService = Depends(get_rag_chat_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatAskResponse:
    try:
        response = rag_chat_service.ask(payload)
        chat_history_service.record_message(
            team_id=payload.team_id,
            user_id=payload.user_id,
            conversation_id=payload.conversation_id,
            channel="ask",
            request_text=payload.question,
            response_text=response.answer,
            request_payload=payload.model_dump(),
            response_payload=response.model_dump(),
        )
        return response
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/action", response_model=ChatActionResponse)
def chat_action(
    payload: ChatActionRequest,
    action_chat_service: ActionChatService = Depends(get_action_chat_service),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatActionResponse:
    try:
        response = action_chat_service.execute(payload)

        response_text = str(response.result.get("message", "")).strip()
        if not response_text:
            response_text = str(response.result)

        chat_history_service.record_message(
            team_id=payload.team_id,
            user_id=payload.user_id,
            conversation_id=payload.conversation_id,
            channel="action",
            request_text=payload.action,
            response_text=response_text,
            request_payload=payload.model_dump(),
            response_payload=response.model_dump(),
        )
        return response
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/history", response_model=ChatHistoryListResponse)
def chat_history(
    team_id: str = Query(min_length=1, max_length=64),
    user_id: str | None = Query(default=None, min_length=1, max_length=64),
    conversation_id: str | None = Query(default=None, min_length=1, max_length=36),
    limit: int = Query(default=20, ge=1, le=200),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatHistoryListResponse:
    try:
        records = chat_history_service.list_history(
            team_id=team_id,
            user_id=user_id,
            conversation_id=conversation_id,
            limit=limit,
        )
        items = [ChatHistoryItem.from_record(item) for item in records]
        return ChatHistoryListResponse.from_result(
            team_id=team_id,
            user_id=user_id,
            conversation_id=conversation_id,
            limit=limit,
            items=items,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
