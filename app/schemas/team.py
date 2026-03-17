from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)


class TeamResponse(BaseModel):
    team_id: str
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
