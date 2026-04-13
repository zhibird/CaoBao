from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SpaceCreate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)


class SpaceUpdate(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, min_length=1, max_length=16)


class SpaceResponse(BaseModel):
    space_id: str
    team_id: str
    owner_user_id: str
    name: str
    description: str | None
    status: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
