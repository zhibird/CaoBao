from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.embedding_model_config import EmbeddingModelConfig
from app.services.embedding_service import EmbeddingRuntimeConfig
from app.services.user_service import UserService


class EmbeddingModelService:
    def __init__(self, db: Session, user_service: UserService) -> None:
        self.db = db
        self.user_service = user_service

    def list_configs(self, *, team_id: str, user_id: str) -> list[EmbeddingModelConfig]:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)

        stmt = (
            select(EmbeddingModelConfig)
            .where(
                EmbeddingModelConfig.team_id == team_id,
                EmbeddingModelConfig.user_id == user_id,
            )
            .order_by(EmbeddingModelConfig.updated_at.desc(), EmbeddingModelConfig.model_name.asc())
        )
        return list(self.db.scalars(stmt).all())

    def upsert_config(
        self,
        *,
        team_id: str,
        user_id: str,
        model_name: str,
        provider: str,
        base_url: str | None,
        api_key: str | None,
    ) -> EmbeddingModelConfig:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)

        normalized_name = model_name.strip()
        normalized_provider = provider.strip().lower()
        normalized_base_url = self._normalize_optional_base_url(base_url)
        normalized_api_key = (api_key or "").strip() or None

        if not normalized_name:
            raise DomainValidationError("model_name cannot be empty.")
        if normalized_name.lower() in {"default", "none"}:
            raise DomainValidationError("'default' and 'none' are reserved and cannot be used as custom embedding models.")
        if not normalized_provider:
            raise DomainValidationError("provider cannot be empty.")

        if normalized_provider != "mock":
            if not normalized_base_url:
                raise DomainValidationError("base_url is required when provider is not 'mock'.")
            if not normalized_api_key:
                raise DomainValidationError("api_key is required when provider is not 'mock'.")

        existing = self._get_by_name(team_id=team_id, user_id=user_id, model_name=normalized_name)
        now = datetime.now(timezone.utc)
        if existing is not None:
            existing.provider = normalized_provider
            existing.base_url = normalized_base_url
            existing.api_key = normalized_api_key
            existing.updated_at = now
            self.db.commit()
            self.db.refresh(existing)
            return existing

        item = EmbeddingModelConfig(
            config_id=str(uuid4()),
            team_id=team_id,
            user_id=user_id,
            model_name=normalized_name,
            provider=normalized_provider,
            base_url=normalized_base_url,
            api_key=normalized_api_key,
            created_at=now,
            updated_at=now,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_config(self, *, team_id: str, user_id: str, model_name: str) -> None:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)

        item = self._get_by_name(team_id=team_id, user_id=user_id, model_name=model_name.strip())
        if item is None:
            raise EntityNotFoundError(f"Embedding model '{model_name}' is not configured for this account.")

        self.db.delete(item)
        self.db.commit()

    def resolve_runtime_config(
        self,
        *,
        team_id: str,
        user_id: str,
        model_name: str | None,
    ) -> EmbeddingRuntimeConfig | None:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)

        if model_name is None:
            return None

        normalized_name = model_name.strip()
        if not normalized_name:
            return None
        if normalized_name.lower() == "default":
            return EmbeddingRuntimeConfig.mock_default()
        if normalized_name.lower() == "none":
            return None

        item = self._get_by_name(team_id=team_id, user_id=user_id, model_name=normalized_name)
        if item is None:
            raise EntityNotFoundError(
                f"Embedding model '{normalized_name}' is not configured for this account."
            )

        if item.provider == "mock":
            return EmbeddingRuntimeConfig.mock_default(model_name=item.model_name)

        return EmbeddingRuntimeConfig(
            provider=item.provider,
            model_name=item.model_name,
            base_url=item.base_url,
            api_key=item.api_key,
        )

    @staticmethod
    def mask_api_key(api_key: str | None) -> str:
        normalized = (api_key or "").strip()
        if not normalized:
            return ""
        if len(normalized) <= 8:
            return "*" * len(normalized)
        return f"{normalized[:4]}...{normalized[-4:]}"

    def _get_by_name(self, *, team_id: str, user_id: str, model_name: str) -> EmbeddingModelConfig | None:
        stmt = select(EmbeddingModelConfig).where(
            EmbeddingModelConfig.team_id == team_id,
            EmbeddingModelConfig.user_id == user_id,
            EmbeddingModelConfig.model_name == model_name,
        )
        return self.db.scalars(stmt).first()

    @staticmethod
    def _normalize_optional_base_url(raw: str | None) -> str | None:
        value = (raw or "").strip().rstrip("/")
        if not value:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DomainValidationError("base_url must be a valid http(s) URL.")
        return value
