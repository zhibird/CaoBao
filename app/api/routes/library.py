from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_document_service, get_space_service
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.schemas.document import DocumentResponse
from app.schemas.library import LibraryPublishRequest
from app.services.document_service import DocumentService
from app.services.space_service import SpaceService

router = APIRouter(prefix="/library")


@router.get("/documents", response_model=list[DocumentResponse])
def list_library_documents(
    team_id: str = Query(min_length=1, max_length=64),
    user_id: str = Query(min_length=1, max_length=64),
    space_id: str = Query(min_length=1, max_length=36),
    limit: int = Query(default=50, ge=1, le=200),
    document_service: DocumentService = Depends(get_document_service),
    space_service: SpaceService = Depends(get_space_service),
) -> list[DocumentResponse]:
    try:
        space_service.ensure_access(space_id=space_id, team_id=team_id, user_id=user_id)
        items = document_service.list_documents(
            team_id=team_id,
            space_id=space_id,
            visibility="space",
            limit=limit,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return [DocumentResponse.model_validate(item) for item in items]


@router.post(
    "/documents/publish-from-conversation",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def publish_library_document(
    payload: LibraryPublishRequest,
    document_service: DocumentService = Depends(get_document_service),
    space_service: SpaceService = Depends(get_space_service),
) -> DocumentResponse:
    try:
        if payload.space_id is not None:
            space_service.ensure_access(
                space_id=payload.space_id,
                team_id=payload.team_id,
                user_id=payload.user_id,
            )
        document = document_service.publish_document_to_library(
            team_id=payload.team_id,
            document_id=payload.document_id,
            conversation_id=payload.conversation_id,
            space_id=payload.space_id,
            source_name=payload.source_name,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DocumentResponse.model_validate(document)
