from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    space_id: str | None = Field(default=None, min_length=1, max_length=36)
    title: str | None = Field(default=None, min_length=1, max_length=255)


class ConversationRename(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)


class ConversationPinUpdate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    pinned: bool


class ConversationResponse(BaseModel):
    conversation_id: str
    team_id: str
    user_id: str
    space_id: str | None
    title: str
    status: str
    is_pinned: bool
    pinned_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
