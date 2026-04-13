from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_conclusion_service,
    get_favorite_service,
    get_memory_service,
    require_current_active_user,
)
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.user import User
from app.schemas.favorite import (
    FavoriteCreate,
    FavoritePromoteResult,
    FavoritePromoteToConclusionRequest,
    FavoritePromoteToMemoryRequest,
    FavoriteResponse,
    FavoriteUpdate,
)
from app.services.favorite_service import FavoriteService
from app.services.conclusion_service import ConclusionService
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/favorites/answers")


@router.post("", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
def create_favorite(
    payload: FavoriteCreate,
    current_user: User = Depends(require_current_active_user),
    favorite_service: FavoriteService = Depends(get_favorite_service),
) -> FavoriteResponse:
    try:
        item = favorite_service.create(
            payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            )
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FavoriteResponse.model_validate(item)


@router.get("", response_model=list[FavoriteResponse])
def list_favorites(
    space_id: str = Query(min_length=1, max_length=36),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_current_active_user),
    favorite_service: FavoriteService = Depends(get_favorite_service),
) -> list[FavoriteResponse]:
    try:
        items = favorite_service.list(
            team_id=current_user.team_id,
            user_id=current_user.user_id,
            space_id=space_id,
            limit=limit,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [FavoriteResponse.model_validate(item) for item in items]


@router.patch("/{favorite_id}", response_model=FavoriteResponse)
def update_favorite(
    favorite_id: str,
    payload: FavoriteUpdate,
    current_user: User = Depends(require_current_active_user),
    favorite_service: FavoriteService = Depends(get_favorite_service),
) -> FavoriteResponse:
    try:
        item = favorite_service.update(
            favorite_id=favorite_id,
            payload=payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            ),
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FavoriteResponse.model_validate(item)


@router.delete(
    "/{favorite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_favorite(
    favorite_id: str,
    current_user: User = Depends(require_current_active_user),
    favorite_service: FavoriteService = Depends(get_favorite_service),
) -> None:
    try:
        favorite_service.delete(
            favorite_id=favorite_id,
            team_id=current_user.team_id,
            user_id=current_user.user_id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{favorite_id}/promote-to-memory", response_model=FavoritePromoteResult)
def promote_favorite_to_memory(
    favorite_id: str,
    payload: FavoritePromoteToMemoryRequest,
    current_user: User = Depends(require_current_active_user),
    favorite_service: FavoriteService = Depends(get_favorite_service),
    memory_service: MemoryService = Depends(get_memory_service),
) -> FavoritePromoteResult:
    try:
        result = favorite_service.promote_to_memory(
            favorite_id=favorite_id,
            payload=payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            ),
            memory_service=memory_service,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return FavoritePromoteResult(
        favorite=FavoriteResponse.model_validate(result["favorite"]),
        result={"memory_id": result.get("memory_id")},
    )


@router.post("/{favorite_id}/promote-to-conclusion", response_model=FavoritePromoteResult)
def promote_favorite_to_conclusion(
    favorite_id: str,
    payload: FavoritePromoteToConclusionRequest,
    current_user: User = Depends(require_current_active_user),
    favorite_service: FavoriteService = Depends(get_favorite_service),
    conclusion_service: ConclusionService = Depends(get_conclusion_service),
) -> FavoritePromoteResult:
    try:
        result = favorite_service.promote_to_conclusion(
            favorite_id=favorite_id,
            payload=payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            ),
            conclusion_service=conclusion_service,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return FavoritePromoteResult(
        favorite=FavoriteResponse.model_validate(result["favorite"]),
        result={"conclusion_id": result.get("conclusion_id")},
    )
