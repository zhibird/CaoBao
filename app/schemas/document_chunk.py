from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunkingRequest(BaseModel):
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    max_chars: int = Field(default=600, ge=100, le=4000)
    overlap: int = Field(default=80, ge=0, le=1000)


class DocumentChunkResponse(BaseModel):
    chunk_id: str
    document_id: str
    team_id: str
    chunk_index: int
    content: str
    start_char: int
    end_char: int
    page_no: int | None = None
    locator_label: str | None = None
    block_type: str | None = None
    meta_json: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkingResult(BaseModel):
    document_id: str
    team_id: str
    total_chunks: int
    chunks: list[DocumentChunkResponse]
