from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_conversation_service, require_current_active_user
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationPinUpdate,
    ConversationRename,
    ConversationResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations")


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(require_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    try:
        item = conversation_service.create(
            team_id=current_user.team_id,
            user_id=current_user.user_id,
            space_id=payload.space_id,
            title=payload.title,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ConversationResponse.model_validate(item)


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    space_id: str | None = Query(default=None, min_length=1, max_length=36),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    try:
        conversations = conversation_service.list(
            team_id=current_user.team_id,
            user_id=current_user.user_id,
            space_id=space_id,
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
    current_user: User = Depends(require_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> None:
    try:
        conversation_service.delete(
            conversation_id=conversation_id,
            team_id=current_user.team_id,
            user_id=current_user.user_id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def rename_conversation(
    conversation_id: str,
    payload: ConversationRename,
    current_user: User = Depends(require_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    try:
        item = conversation_service.rename(
            conversation_id=conversation_id,
            team_id=current_user.team_id,
            user_id=current_user.user_id,
            title=payload.title,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ConversationResponse.model_validate(item)


@router.patch("/{conversation_id}/pin", response_model=ConversationResponse)
def update_pin_conversation(
    conversation_id: str,
    payload: ConversationPinUpdate,
    current_user: User = Depends(require_current_active_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    try:
        item = conversation_service.pin(
            conversation_id=conversation_id,
            team_id=current_user.team_id,
            user_id=current_user.user_id,
            pinned=payload.pinned,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ConversationResponse.model_validate(item)
