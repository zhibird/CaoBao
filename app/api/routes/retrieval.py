from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_retrieval_service
from app.core.exceptions import EntityNotFoundError
from app.schemas.retrieval import (
    RetrievalIndexRequest,
    RetrievalIndexResult,
    RetrievalSearchRequest,
    RetrievalSearchResult,
)
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieval")


@router.post("/index", response_model=RetrievalIndexResult)
def index_chunks(
    payload: RetrievalIndexRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalIndexResult:
    try:
        indexed = retrieval_service.index_chunks(
            team_id=payload.team_id,
            document_id=payload.document_id,
            conversation_id=payload.conversation_id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RetrievalIndexResult(
        team_id=payload.team_id,
        conversation_id=payload.conversation_id,
        document_id=payload.document_id,
        indexed_chunks=indexed,
    )


@router.post("/search", response_model=RetrievalSearchResult)
def search_chunks(
    payload: RetrievalSearchRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalSearchResult:
    try:
        hits = retrieval_service.search_chunks(
            team_id=payload.team_id,
            query=payload.query,
            top_k=payload.top_k,
            document_id=payload.document_id,
            conversation_id=payload.conversation_id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RetrievalSearchResult(
        team_id=payload.team_id,
        conversation_id=payload.conversation_id,
        query=payload.query,
        top_k=payload.top_k,
        hits=hits,
    )
