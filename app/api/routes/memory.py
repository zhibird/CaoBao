from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_memory_service, require_current_active_user
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.user import User
from app.schemas.memory import MemoryCardCreate, MemoryCardResponse, MemoryCardUpdate
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory/cards")


@router.post("", response_model=MemoryCardResponse, status_code=status.HTTP_201_CREATED)
def create_memory_card(
    payload: MemoryCardCreate,
    current_user: User = Depends(require_current_active_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryCardResponse:
    try:
        item = memory_service.create(
            payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            )
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MemoryCardResponse.model_validate(item)


@router.get("", response_model=list[MemoryCardResponse])
def list_memory_cards(
    space_id: str = Query(min_length=1, max_length=36),
    status_filter: str | None = Query(default=None, alias="status", min_length=1, max_length=16),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_current_active_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> list[MemoryCardResponse]:
    try:
        items = memory_service.list(
            team_id=current_user.team_id,
            user_id=current_user.user_id,
            space_id=space_id,
            status=status_filter,
            limit=limit,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [MemoryCardResponse.model_validate(item) for item in items]


@router.patch("/{memory_id}", response_model=MemoryCardResponse)
def update_memory_card(
    memory_id: str,
    payload: MemoryCardUpdate,
    current_user: User = Depends(require_current_active_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryCardResponse:
    try:
        item = memory_service.update(
            memory_id=memory_id,
            payload=payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            ),
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MemoryCardResponse.model_validate(item)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory_card(
    memory_id: str,
    current_user: User = Depends(require_current_active_user),
    memory_service: MemoryService = Depends(get_memory_service),
) -> None:
    try:
        memory_service.delete(
            memory_id=memory_id,
            team_id=current_user.team_id,
            user_id=current_user.user_id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
