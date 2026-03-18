from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=255)


class ConversationRename(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    conversation_id: str
    team_id: str
    user_id: str
    title: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
