from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FavoriteCreate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    space_id: str = Field(min_length=1, max_length=36)
    message_id: str = Field(min_length=1, max_length=36)
    title: str | None = Field(default=None, max_length=128)
    note: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = None


class FavoriteUpdate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, max_length=128)
    note: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = None


class FavoritePromoteToMemoryRequest(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    space_id: str | None = Field(default=None, min_length=1, max_length=36)
    category: str = Field(default="fact", min_length=1, max_length=32)
    title: str | None = Field(default=None, max_length=128)
    summary: str | None = Field(default=None, max_length=2000)
    weight: float = Field(default=0.8, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="active", min_length=1, max_length=16)
    expires_at: datetime | None = None


class FavoritePromoteToConclusionRequest(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    space_id: str | None = Field(default=None, min_length=1, max_length=36)
    title: str | None = Field(default=None, max_length=128)
    topic: str | None = Field(default=None, max_length=128)
    summary: str | None = Field(default=None, max_length=4000)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="draft", min_length=1, max_length=16)


class FavoriteResponse(BaseModel):
    favorite_id: str
    team_id: str
    space_id: str
    user_id: str
    conversation_id: str | None
    message_id: str
    title: str
    question_text: str
    answer_text: str
    sources_json: str | None
    note: str | None
    tags_json: str | None
    is_promoted: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FavoritePromoteResult(BaseModel):
    favorite: FavoriteResponse
    result: dict[str, Any]

