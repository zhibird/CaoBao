from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConclusionCreate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    space_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=128)
    topic: str | None = Field(default=None, max_length=128)
    content: str = Field(min_length=1, max_length=12000)
    summary: str | None = Field(default=None, max_length=4000)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    status: str = Field(default="draft", min_length=1, max_length=16)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    source_message_id: str | None = Field(default=None, min_length=1, max_length=36)
    source_favorite_id: str | None = Field(default=None, min_length=1, max_length=36)
    evidence: dict[str, Any] | None = None
    tags: list[str] | None = None


class ConclusionUpdate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=128)
    topic: str | None = Field(default=None, max_length=128)
    content: str | None = Field(default=None, min_length=1, max_length=12000)
    summary: str | None = Field(default=None, max_length=4000)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: str | None = Field(default=None, min_length=1, max_length=16)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    evidence: dict[str, Any] | None = None
    tags: list[str] | None = None


class ConclusionConfirmRequest(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    target_status: str = Field(default="effective", min_length=1, max_length=16)


class ConclusionArchiveRequest(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)


class ConclusionResponse(BaseModel):
    conclusion_id: str
    team_id: str
    space_id: str
    user_id: str
    title: str
    topic: str
    content: str
    summary: str | None
    status: str
    confidence: float
    effective_from: datetime | None
    effective_to: datetime | None
    source_message_id: str | None
    source_favorite_id: str | None
    evidence_json: str | None
    tags_json: str | None
    doc_sync_document_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
