from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_chunk_service, get_document_service
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.schemas.document import DocumentImportRequest, DocumentResponse
from app.schemas.document_chunk import (
    DocumentChunkingRequest,
    DocumentChunkingResult,
    DocumentChunkResponse,
)
from app.services.chunk_service import ChunkService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents")


@router.post("/import", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def import_document(
    payload: DocumentImportRequest,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        document = document_service.import_document(payload)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    team_id: str = Query(min_length=1, max_length=64),
    document_service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    documents = document_service.list_documents(team_id=team_id)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    team_id: str = Query(min_length=1, max_length=64),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        document = document_service.get_document_in_team(
            document_id=document_id,
            team_id=team_id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DocumentResponse.model_validate(document)


@router.post("/{document_id}/chunk", response_model=DocumentChunkingResult)
def chunk_document(
    document_id: str,
    payload: DocumentChunkingRequest,
    chunk_service: ChunkService = Depends(get_chunk_service),
) -> DocumentChunkingResult:
    try:
        chunks = chunk_service.chunk_document(
            document_id=document_id,
            team_id=payload.team_id,
            max_chars=payload.max_chars,
            overlap=payload.overlap,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DocumentChunkingResult(
        document_id=document_id,
        team_id=payload.team_id,
        total_chunks=len(chunks),
        chunks=[DocumentChunkResponse.model_validate(chunk) for chunk in chunks],
    )


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkResponse])
def list_chunks(
    document_id: str,
    team_id: str = Query(min_length=1, max_length=64),
    chunk_service: ChunkService = Depends(get_chunk_service),
) -> list[DocumentChunkResponse]:
    try:
        chunks = chunk_service.list_chunks(document_id=document_id, team_id=team_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [DocumentChunkResponse.model_validate(chunk) for chunk in chunks]