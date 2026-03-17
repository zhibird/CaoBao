from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    team_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    role: str = Field(default="member", min_length=1, max_length=32)


class UserResponse(BaseModel):
    user_id: str
    team_id: str
    display_name: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
