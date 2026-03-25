import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.retrieval import RetrievalHit


class ChatEchoRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    team_id: str = Field(min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    message: str = Field(min_length=1, max_length=2000)


class ChatEchoResponse(BaseModel):
    user_id: str
    team_id: str
    conversation_id: str | None = None
    answer: str
    created_at: str

    @classmethod
    def from_message(
        cls,
        user_id: str,
        team_id: str,
        answer: str,
        conversation_id: str | None = None,
    ) -> "ChatEchoResponse":
        return cls(
            user_id=user_id,
            team_id=team_id,
            conversation_id=conversation_id,
            answer=answer,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class ChatAskRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    team_id: str = Field(min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: str | None = Field(default=None, min_length=1, max_length=36)
    selected_document_ids: list[str] | None = None
    model: str | None = Field(default=None, min_length=1, max_length=128)
    embedding_model: str | None = Field(default=None, min_length=1, max_length=128)


class ChatSource(BaseModel):
    document_id: str
    source_name: str | None = None
    chunk_id: str
    chunk_index: int
    page_no: int | None = None
    locator_label: str | None = None
    snippet: str | None = None
    score: float


class ChatContentPart(BaseModel):
    type: Literal["text", "image"]
    text: str | None = None
    url: str | None = None
    mime_type: str | None = None
    alt: str | None = None


class ChatAskResponse(BaseModel):
    user_id: str
    team_id: str
    conversation_id: str | None = None
    question: str
    answer: str
    content_parts: list[ChatContentPart] = Field(default_factory=list)
    hits: list[RetrievalHit]
    mode: str
    sources: list[ChatSource]
    model: str | None = None
    created_at: str

    @classmethod
    def from_result(
        cls,
        user_id: str,
        team_id: str,
        conversation_id: str | None,
        question: str,
        answer: str,
        content_parts: list[ChatContentPart] | None,
        hits: list[RetrievalHit],
        mode: str,
        sources: list[ChatSource],
        model: str | None = None,
    ) -> "ChatAskResponse":
        return cls(
            user_id=user_id,
            team_id=team_id,
            conversation_id=conversation_id,
            question=question,
            answer=answer,
            content_parts=content_parts or [],
            hits=hits,
            mode=mode,
            sources=sources,
            model=model,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class ChatActionRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    team_id: str = Field(min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    action: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ChatActionResponse(BaseModel):
    user_id: str
    team_id: str
    conversation_id: str | None = None
    action: str
    result: dict[str, Any]
    created_at: str

    @classmethod
    def from_result(
        cls,
        *,
        user_id: str,
        team_id: str,
        conversation_id: str | None,
        action: str,
        result: dict[str, Any],
    ) -> "ChatActionResponse":
        return cls(
            user_id=user_id,
            team_id=team_id,
            conversation_id=conversation_id,
            action=action,
            result=result,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class ChatHistoryItem(BaseModel):
    message_id: str
    team_id: str
    user_id: str
    conversation_id: str | None
    channel: str
    request_text: str
    response_text: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    created_at: str

    @classmethod
    def from_record(cls, record: Any) -> "ChatHistoryItem":
        return cls(
            message_id=record.message_id,
            team_id=record.team_id,
            user_id=record.user_id,
            conversation_id=record.conversation_id,
            channel=record.channel,
            request_text=record.request_text,
            response_text=record.response_text,
            request_payload=_safe_json_loads(record.request_payload_json),
            response_payload=_safe_json_loads(record.response_payload_json),
            created_at=record.created_at.isoformat(),
        )


class ChatHistoryListResponse(BaseModel):
    team_id: str
    user_id: str | None
    conversation_id: str | None
    limit: int
    items: list[ChatHistoryItem]

    @classmethod
    def from_result(
        cls,
        *,
        team_id: str,
        user_id: str | None,
        conversation_id: str | None,
        limit: int,
        items: list[ChatHistoryItem],
    ) -> "ChatHistoryListResponse":
        return cls(
            team_id=team_id,
            user_id=user_id,
            conversation_id=conversation_id,
            limit=limit,
            items=items,
        )


class ChatHistoryEditRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    request_text: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    document_id: str | None = Field(default=None, min_length=1, max_length=36)
    selected_document_ids: list[str] | None = None
    model: str | None = Field(default=None, min_length=1, max_length=128)
    embedding_model: str | None = Field(default=None, min_length=1, max_length=128)


def _safe_json_loads(raw: str) -> dict[str, Any]:
    try:
        decoded = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}

    if isinstance(decoded, dict):
        return decoded

    return {}
