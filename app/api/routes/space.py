from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_space_service
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.schemas.space import SpaceCreate, SpaceResponse, SpaceUpdate
from app.services.space_service import SpaceService

router = APIRouter(prefix="/spaces")


@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
def create_space(
    payload: SpaceCreate,
    space_service: SpaceService = Depends(get_space_service),
) -> SpaceResponse:
    try:
        item = space_service.create(payload)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SpaceResponse.model_validate(item)


@router.get("", response_model=list[SpaceResponse])
def list_spaces(
    team_id: str = Query(min_length=1, max_length=64),
    user_id: str = Query(min_length=1, max_length=64),
    limit: int = Query(default=100, ge=1, le=200),
    space_service: SpaceService = Depends(get_space_service),
) -> list[SpaceResponse]:
    try:
        items = space_service.list(team_id=team_id, user_id=user_id, limit=limit)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [SpaceResponse.model_validate(item) for item in items]


@router.patch("/{space_id}", response_model=SpaceResponse)
def update_space(
    space_id: str,
    payload: SpaceUpdate,
    space_service: SpaceService = Depends(get_space_service),
) -> SpaceResponse:
    try:
        item = space_service.update(space_id=space_id, payload=payload)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SpaceResponse.model_validate(item)


@router.delete("/{space_id}", response_model=SpaceResponse)
def delete_space(
    space_id: str,
    team_id: str = Query(min_length=1, max_length=64),
    user_id: str = Query(min_length=1, max_length=64),
    space_service: SpaceService = Depends(get_space_service),
) -> SpaceResponse:
    try:
        item = space_service.delete(space_id=space_id, team_id=team_id, user_id=user_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SpaceResponse.model_validate(item)
