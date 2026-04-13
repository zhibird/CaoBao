from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemoryCardCreate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    space_id: str = Field(min_length=1, max_length=36)
    category: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=4000)
    summary: str | None = Field(default=None, max_length=2000)
    weight: float = Field(default=0.8, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="active", min_length=1, max_length=16)
    source_message_id: str | None = Field(default=None, min_length=1, max_length=36)
    expires_at: datetime | None = None


class MemoryCardUpdate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    category: str | None = Field(default=None, min_length=1, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=128)
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    summary: str | None = Field(default=None, max_length=2000)
    weight: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: str | None = Field(default=None, min_length=1, max_length=16)
    expires_at: datetime | None = None


class MemoryCardResponse(BaseModel):
    memory_id: str
    team_id: str
    space_id: str | None
    user_id: str
    category: str
    title: str
    content: str
    summary: str | None
    weight: float
    confidence: float
    status: str
    source_message_id: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
