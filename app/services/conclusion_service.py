from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.models.chat_history import ChatHistory
from app.models.conclusion import Conclusion
from app.models.document import Document
from app.schemas.conclusion import (
    ConclusionArchiveRequest,
    ConclusionConfirmRequest,
    ConclusionCreate,
    ConclusionUpdate,
)
from app.services.space_service import SpaceService
from app.services.user_service import UserService


class ConclusionService:
    _ALLOWED_STATUSES = {"draft", "confirmed", "effective", "superseded", "archived"}
    _ALLOWED_CONFIRM_TARGETS = {"confirmed", "effective"}

    def __init__(
        self,
        db: Session,
        user_service: UserService,
        space_service: SpaceService,
        document_service=None,
        chunk_service=None,
        retrieval_service=None,
    ) -> None:
        self.db = db
        self.user_service = user_service
        self.space_service = space_service
        self.document_service = document_service
        self.chunk_service = chunk_service
        self.retrieval_service = retrieval_service

    def create(self, payload: ConclusionCreate) -> Conclusion:
        self.space_service.ensure_access(
            space_id=payload.space_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )
        self._validate_source_message(
            source_message_id=payload.source_message_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )

        now = datetime.now(timezone.utc)
        item = Conclusion(
            conclusion_id=str(uuid4()),
            team_id=payload.team_id,
            space_id=payload.space_id,
            user_id=payload.user_id,
            title=payload.title.strip(),
            topic=(payload.topic or "").strip(),
            content=payload.content.strip(),
            summary=(payload.summary or "").strip() or None,
            status=self._normalize_status(payload.status),
            confidence=float(payload.confidence),
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            source_message_id=payload.source_message_id,
            source_favorite_id=payload.source_favorite_id,
            evidence_json=self._encode_json(payload.evidence),
            tags_json=self._encode_json(payload.tags),
            doc_sync_document_id=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(
        self,
        *,
        team_id: str,
        user_id: str,
        space_id: str,
        status: str | None,
        limit: int,
    ) -> list[Conclusion]:
        self.space_service.ensure_access(space_id=space_id, team_id=team_id, user_id=user_id)
        if limit < 1 or limit > 200:
            raise DomainValidationError("limit must be between 1 and 200.")

        stmt = select(Conclusion).where(
            Conclusion.team_id == team_id,
            Conclusion.user_id == user_id,
            Conclusion.space_id == space_id,
        )
        if status is not None:
            stmt = stmt.where(Conclusion.status == self._normalize_status(status))
        stmt = stmt.order_by(Conclusion.updated_at.desc(), Conclusion.conclusion_id.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def update(self, *, conclusion_id: str, payload: ConclusionUpdate) -> Conclusion:
        item = self.ensure_access(
            conclusion_id=conclusion_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )
        if payload.title is not None:
            item.title = payload.title.strip()
        if payload.topic is not None:
            item.topic = payload.topic.strip()
        if payload.content is not None:
            item.content = payload.content.strip()
        if payload.summary is not None:
            item.summary = payload.summary.strip() or None
        if payload.status is not None:
            item.status = self._normalize_status(payload.status)
        if payload.confidence is not None:
            item.confidence = float(payload.confidence)
        if payload.effective_from is not None:
            item.effective_from = payload.effective_from
        if payload.effective_to is not None:
            item.effective_to = payload.effective_to
        if payload.evidence is not None:
            item.evidence_json = self._encode_json(payload.evidence)
        if payload.tags is not None:
            item.tags_json = self._encode_json(payload.tags)

        item.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(item)
        return item

    def confirm(self, *, conclusion_id: str, payload: ConclusionConfirmRequest) -> Conclusion:
        item = self.ensure_access(
            conclusion_id=conclusion_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )
        target_status = payload.target_status.strip().lower()
        if target_status not in self._ALLOWED_CONFIRM_TARGETS:
            raise DomainValidationError("target_status must be one of: confirmed, effective.")

        item.status = target_status
        if target_status == "effective" and item.effective_from is None:
            item.effective_from = datetime.now(timezone.utc)
        item.updated_at = datetime.now(timezone.utc)

        document = self._upsert_sync_document(item)
        item.doc_sync_document_id = document.document_id
        self._sync_document_for_retrieval(document=document, user_id=payload.user_id)

        self.db.commit()
        self.db.refresh(item)
        return item

    def archive(self, *, conclusion_id: str, payload: ConclusionArchiveRequest) -> Conclusion:
        item = self.ensure_access(
            conclusion_id=conclusion_id,
            team_id=payload.team_id,
            user_id=payload.user_id,
        )
        item.status = "archived"
        item.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_from_favorite(
        self,
        *,
        favorite,
        team_id: str,
        user_id: str,
        space_id: str,
        title: str | None,
        topic: str | None,
        summary: str | None,
        confidence: float,
        status: str,
    ) -> Conclusion:
        self.space_service.ensure_access(space_id=space_id, team_id=team_id, user_id=user_id)
        target_status = self._normalize_status(status)

        now = datetime.now(timezone.utc)
        item = Conclusion(
            conclusion_id=str(uuid4()),
            team_id=team_id,
            space_id=space_id,
            user_id=user_id,
            title=(title or "").strip() or str(getattr(favorite, "title", "")).strip() or "Conclusion",
            topic=(topic or "").strip() or "favorite-promotion",
            content=str(getattr(favorite, "answer_text", "")).strip(),
            summary=(summary or "").strip() or None,
            status=target_status,
            confidence=float(confidence),
            effective_from=now if target_status == "effective" else None,
            effective_to=None,
            source_message_id=str(getattr(favorite, "message_id", "")).strip() or None,
            source_favorite_id=str(getattr(favorite, "favorite_id", "")).strip() or None,
            evidence_json=getattr(favorite, "sources_json", None),
            tags_json=getattr(favorite, "tags_json", None),
            doc_sync_document_id=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(item)
        if target_status in self._ALLOWED_CONFIRM_TARGETS:
            document = self._upsert_sync_document(item)
            item.doc_sync_document_id = document.document_id
            self._sync_document_for_retrieval(document=document, user_id=user_id)
        self.db.commit()
        self.db.refresh(item)
        return item

    def ensure_access(self, *, conclusion_id: str, team_id: str, user_id: str) -> Conclusion:
        self.user_service.ensure_user_in_team(user_id=user_id, team_id=team_id)
        item = self.db.get(Conclusion, conclusion_id)
        if item is None:
            raise EntityNotFoundError(f"Conclusion '{conclusion_id}' not found.")
        if item.team_id != team_id or item.user_id != user_id:
            raise DomainValidationError("Conclusion does not belong to the provided team/user.")
        self.space_service.ensure_access(space_id=item.space_id, team_id=team_id, user_id=user_id)
        return item

    def _normalize_status(self, status: str) -> str:
        normalized = status.strip().lower()
        if normalized not in self._ALLOWED_STATUSES:
            raise DomainValidationError(
                "status must be one of: draft, confirmed, effective, superseded, archived."
            )
        return normalized

    def _encode_json(self, payload: object) -> str | None:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _validate_source_message(
        self,
        *,
        source_message_id: str | None,
        team_id: str,
        user_id: str,
    ) -> None:
        normalized_id = (source_message_id or "").strip()
        if not normalized_id:
            return
        message = self.db.get(ChatHistory, normalized_id)
        if message is None:
            raise EntityNotFoundError(f"Message '{normalized_id}' does not exist.")
        if message.team_id != team_id or message.user_id != user_id:
            raise DomainValidationError("Source message does not belong to the provided team/user.")

    def _upsert_sync_document(self, item: Conclusion) -> Document:
        markdown_content = self._build_conclusion_markdown(item)
        now = datetime.now(timezone.utc)
        digest = hashlib.sha256(markdown_content.encode("utf-8")).hexdigest()
        size_bytes = len(markdown_content.encode("utf-8"))
        source_name = f"conclusion-{item.conclusion_id}.md"

        existing: Document | None = None
        if item.doc_sync_document_id:
            existing = self.db.get(Document, item.doc_sync_document_id)
        if existing is None:
            existing = self.db.scalar(
                select(Document).where(
                    Document.team_id == item.team_id,
                    Document.space_id == item.space_id,
                    Document.asset_kind == "conclusion_note",
                    Document.source_name == source_name,
                )
            )

        if existing is None:
            existing = Document(
                document_id=str(uuid4()),
                team_id=item.team_id,
                conversation_id=None,
                space_id=item.space_id,
                source_name=source_name,
                content_type="md",
                mime_type="text/markdown",
                size_bytes=size_bytes,
                sha256=digest,
                storage_key=f"inline://conclusion/{item.conclusion_id}",
                preview_key=None,
                page_count=None,
                failure_stage=None,
                error_code=None,
                error_message=None,
                meta_json=None,
                visibility="space",
                asset_kind="conclusion_note",
                retrieval_enabled=True,
                origin_document_id=None,
                status="uploaded",
                content=markdown_content,
                created_at=now,
                updated_at=now,
            )
            self.db.add(existing)
            return existing

        existing.source_name = source_name
        existing.content_type = "md"
        existing.mime_type = "text/markdown"
        existing.size_bytes = size_bytes
        existing.sha256 = digest
        existing.storage_key = f"inline://conclusion/{item.conclusion_id}"
        existing.visibility = "space"
        existing.asset_kind = "conclusion_note"
        existing.retrieval_enabled = True
        existing.status = "uploaded"
        existing.content = markdown_content
        existing.updated_at = now
        self.db.add(existing)
        return existing

    def _build_conclusion_markdown(self, item: Conclusion) -> str:
        lines = [f"# {item.title}", ""]
        topic = item.topic.strip()
        if topic:
            lines.append(f"- Topic: {topic}")
        lines.append(f"- Status: {item.status}")
        lines.append(f"- Confidence: {item.confidence:.2f}")
        if item.effective_from is not None:
            lines.append(f"- Effective From: {item.effective_from.isoformat()}")
        if item.effective_to is not None:
            lines.append(f"- Effective To: {item.effective_to.isoformat()}")
        lines.extend(["", "## Conclusion", "", item.content.strip()])
        if item.summary:
            lines.extend(["", "## Summary", "", item.summary.strip()])
        if item.evidence_json:
            lines.extend(["", "## Evidence", "", item.evidence_json])
        if item.tags_json:
            lines.extend(["", "## Tags", "", item.tags_json])
        return "\n".join(lines).strip()

    def _sync_document_for_retrieval(self, *, document: Document, user_id: str) -> None:
        if self.document_service is None or self.chunk_service is None or self.retrieval_service is None:
            return
        self.db.flush()
        self.document_service.process_document_pipeline(
            document_id=document.document_id,
            team_id=document.team_id,
            conversation_id=None,
            user_id=user_id,
            auto_index=True,
            embedding_model=None,
            chunk_service=self.chunk_service,
            retrieval_service=self.retrieval_service,
        )
