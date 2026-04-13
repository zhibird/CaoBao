from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_space_service, require_current_active_user
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.user import User
from app.schemas.space import SpaceCreate, SpaceResponse, SpaceUpdate
from app.services.space_service import SpaceService

router = APIRouter(prefix="/spaces")
_SPACE_OWNERSHIP_ERROR = "Space does not belong to the provided team/user."


@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
def create_space(
    payload: SpaceCreate,
    current_user: User = Depends(require_current_active_user),
    space_service: SpaceService = Depends(get_space_service),
) -> SpaceResponse:
    try:
        effective_payload = payload.model_copy(
            update={"team_id": current_user.team_id, "user_id": current_user.user_id}
        )
        item = space_service.create(effective_payload)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SpaceResponse.model_validate(item)


@router.get("", response_model=list[SpaceResponse])
def list_spaces(
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(require_current_active_user),
    space_service: SpaceService = Depends(get_space_service),
) -> list[SpaceResponse]:
    try:
        items = space_service.list(
            team_id=current_user.team_id,
            user_id=current_user.user_id,
            limit=limit,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [SpaceResponse.model_validate(item) for item in items]


@router.patch("/{space_id}", response_model=SpaceResponse)
def update_space(
    space_id: str,
    payload: SpaceUpdate,
    current_user: User = Depends(require_current_active_user),
    space_service: SpaceService = Depends(get_space_service),
) -> SpaceResponse:
    try:
        effective_payload = payload.model_copy(
            update={"team_id": current_user.team_id, "user_id": current_user.user_id}
        )
        item = space_service.update(space_id=space_id, payload=effective_payload)
    except EntityNotFoundError as exc:
        raise _space_not_found(space_id) from exc
    except DomainValidationError as exc:
        if str(exc) == _SPACE_OWNERSHIP_ERROR:
            raise _space_not_found(space_id) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SpaceResponse.model_validate(item)


@router.delete("/{space_id}", response_model=SpaceResponse)
def delete_space(
    space_id: str,
    current_user: User = Depends(require_current_active_user),
    space_service: SpaceService = Depends(get_space_service),
) -> SpaceResponse:
    try:
        item = space_service.delete(
            space_id=space_id,
            team_id=current_user.team_id,
            user_id=current_user.user_id,
        )
    except EntityNotFoundError as exc:
        raise _space_not_found(space_id) from exc
    except DomainValidationError as exc:
        if str(exc) == _SPACE_OWNERSHIP_ERROR:
            raise _space_not_found(space_id) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SpaceResponse.model_validate(item)


def _space_not_found(space_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Space '{space_id}' not found.",
    )
