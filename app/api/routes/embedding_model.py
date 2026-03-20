from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_embedding_model_service
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.schemas.embedding_model import (
    EmbeddingModelConfigItem,
    EmbeddingModelConfigListResponse,
    EmbeddingModelConfigUpsertRequest,
)
from app.services.embedding_model_service import EmbeddingModelService

router = APIRouter(prefix="/embedding/models")


@router.get("", response_model=EmbeddingModelConfigListResponse)
def list_embedding_models(
    team_id: str = Query(min_length=1, max_length=64),
    user_id: str = Query(min_length=1, max_length=64),
    embedding_model_service: EmbeddingModelService = Depends(get_embedding_model_service),
) -> EmbeddingModelConfigListResponse:
    try:
        items = embedding_model_service.list_configs(team_id=team_id, user_id=user_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return EmbeddingModelConfigListResponse(
        team_id=team_id,
        user_id=user_id,
        items=[
            EmbeddingModelConfigItem(
                config_id=item.config_id,
                team_id=item.team_id,
                user_id=item.user_id,
                model_name=item.model_name,
                provider=item.provider,
                base_url=item.base_url,
                has_api_key=bool((item.api_key or "").strip()),
                masked_api_key=embedding_model_service.mask_api_key(item.api_key),
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ],
    )


@router.post("", response_model=EmbeddingModelConfigItem)
def upsert_embedding_model(
    payload: EmbeddingModelConfigUpsertRequest,
    embedding_model_service: EmbeddingModelService = Depends(get_embedding_model_service),
) -> EmbeddingModelConfigItem:
    try:
        item = embedding_model_service.upsert_config(
            team_id=payload.team_id,
            user_id=payload.user_id,
            model_name=payload.model_name,
            provider=payload.provider,
            base_url=payload.base_url,
            api_key=payload.api_key,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return EmbeddingModelConfigItem(
        config_id=item.config_id,
        team_id=item.team_id,
        user_id=item.user_id,
        model_name=item.model_name,
        provider=item.provider,
        base_url=item.base_url,
        has_api_key=bool((item.api_key or "").strip()),
        masked_api_key=embedding_model_service.mask_api_key(item.api_key),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/{model_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_embedding_model(
    model_name: str,
    team_id: str = Query(min_length=1, max_length=64),
    user_id: str = Query(min_length=1, max_length=64),
    embedding_model_service: EmbeddingModelService = Depends(get_embedding_model_service),
) -> None:
    try:
        embedding_model_service.delete_config(
            team_id=team_id,
            user_id=user_id,
            model_name=model_name,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
