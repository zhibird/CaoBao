from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentImportRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    space_id: str | None = Field(default=None, min_length=1, max_length=36)
    source_name: str = Field(min_length=1, max_length=255)
    content_type: Literal["txt", "md"]
    content: str = Field(min_length=1, max_length=200_000)
    auto_index: bool = False
    embedding_model: str | None = Field(default=None, min_length=1, max_length=128)


class DocumentResponse(BaseModel):
    document_id: str
    team_id: str
    conversation_id: str | None
    space_id: str | None
    source_name: str
    content_type: str
    mime_type: str
    size_bytes: int
    visibility: str
    asset_kind: str
    retrieval_enabled: bool
    origin_document_id: str | None
    status: str
    content: str
    page_count: int | None
    failure_stage: str | None
    error_code: str | None
    error_message: str | None
    meta_json: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
