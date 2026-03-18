from pydantic import BaseModel, Field


class RetrievalIndexRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    document_id: str | None = Field(default=None, min_length=1, max_length=36)


class RetrievalIndexResult(BaseModel):
    team_id: str
    conversation_id: str | None
    document_id: str | None
    indexed_chunks: int


class RetrievalSearchRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: str | None = Field(default=None, min_length=1, max_length=36)


class RetrievalHit(BaseModel):
    chunk_id: str
    document_id: str
    team_id: str
    chunk_index: int
    content: str
    score: float


class RetrievalSearchResult(BaseModel):
    team_id: str
    conversation_id: str | None
    query: str
    top_k: int
    hits: list[RetrievalHit]
