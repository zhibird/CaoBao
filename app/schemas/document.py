from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentImportRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    source_name: str = Field(min_length=1, max_length=255)
    content_type: Literal["txt", "md"]
    content: str = Field(min_length=1, max_length=200_000)


class DocumentResponse(BaseModel):
    document_id: str
    team_id: str
    conversation_id: str | None
    source_name: str
    content_type: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
