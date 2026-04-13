from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_conclusion_service, require_current_active_user
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.user import User
from app.schemas.conclusion import (
    ConclusionArchiveRequest,
    ConclusionConfirmRequest,
    ConclusionCreate,
    ConclusionResponse,
    ConclusionUpdate,
)
from app.services.conclusion_service import ConclusionService

router = APIRouter(prefix="/conclusions")


@router.post("", response_model=ConclusionResponse, status_code=status.HTTP_201_CREATED)
def create_conclusion(
    payload: ConclusionCreate,
    current_user: User = Depends(require_current_active_user),
    conclusion_service: ConclusionService = Depends(get_conclusion_service),
) -> ConclusionResponse:
    try:
        item = conclusion_service.create(
            payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            )
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ConclusionResponse.model_validate(item)


@router.get("", response_model=list[ConclusionResponse])
def list_conclusions(
    space_id: str = Query(min_length=1, max_length=36),
    status_filter: str | None = Query(default=None, alias="status", min_length=1, max_length=16),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_current_active_user),
    conclusion_service: ConclusionService = Depends(get_conclusion_service),
) -> list[ConclusionResponse]:
    try:
        items = conclusion_service.list(
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
    return [ConclusionResponse.model_validate(item) for item in items]


@router.patch("/{conclusion_id}", response_model=ConclusionResponse)
def update_conclusion(
    conclusion_id: str,
    payload: ConclusionUpdate,
    current_user: User = Depends(require_current_active_user),
    conclusion_service: ConclusionService = Depends(get_conclusion_service),
) -> ConclusionResponse:
    try:
        item = conclusion_service.update(
            conclusion_id=conclusion_id,
            payload=payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            ),
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ConclusionResponse.model_validate(item)


@router.post("/{conclusion_id}/confirm", response_model=ConclusionResponse)
def confirm_conclusion(
    conclusion_id: str,
    payload: ConclusionConfirmRequest,
    current_user: User = Depends(require_current_active_user),
    conclusion_service: ConclusionService = Depends(get_conclusion_service),
) -> ConclusionResponse:
    try:
        item = conclusion_service.confirm(
            conclusion_id=conclusion_id,
            payload=payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            ),
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ConclusionResponse.model_validate(item)


@router.post("/{conclusion_id}/archive", response_model=ConclusionResponse)
def archive_conclusion(
    conclusion_id: str,
    payload: ConclusionArchiveRequest,
    current_user: User = Depends(require_current_active_user),
    conclusion_service: ConclusionService = Depends(get_conclusion_service),
) -> ConclusionResponse:
    try:
        item = conclusion_service.archive(
            conclusion_id=conclusion_id,
            payload=payload.model_copy(
                update={"team_id": current_user.team_id, "user_id": current_user.user_id}
            ),
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ConclusionResponse.model_validate(item)
