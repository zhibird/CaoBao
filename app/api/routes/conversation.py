from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_conversation_service
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.schemas.conversation import ConversationCreate, ConversationRename, ConversationResponse
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations")


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    try:
        item = conversation_service.create(
            team_id=payload.team_id,
            user_id=payload.user_id,
            title=payload.title,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ConversationResponse.model_validate(item)


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    team_id: str = Query(min_length=1, max_length=64),
    user_id: str = Query(min_length=1, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    try:
        conversations = conversation_service.list(
            team_id=team_id,
            user_id=user_id,
            limit=limit,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return [ConversationResponse.model_validate(item) for item in conversations]


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    team_id: str = Query(min_length=1, max_length=64),
    user_id: str = Query(min_length=1, max_length=64),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> None:
    try:
        conversation_service.delete(
            conversation_id=conversation_id,
            team_id=team_id,
            user_id=user_id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def rename_conversation(
    conversation_id: str,
    payload: ConversationRename,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    try:
        item = conversation_service.rename(
            conversation_id=conversation_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
            title=payload.title,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ConversationResponse.model_validate(item)
