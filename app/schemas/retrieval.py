from pydantic import BaseModel, Field


class RetrievalIndexRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    document_id: str | None = Field(default=None, min_length=1, max_length=36)
    document_ids: list[str] | None = None
    embedding_model: str | None = Field(default=None, min_length=1, max_length=128)
    rebuild: bool = False


class RetrievalIndexResult(BaseModel):
    team_id: str
    user_id: str | None
    conversation_id: str | None
    document_id: str | None
    embedding_model: str | None
    indexed_chunks: int


class RetrievalSearchRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: str | None = Field(default=None, min_length=1, max_length=36)
    document_ids: list[str] | None = None
    embedding_model: str | None = Field(default=None, min_length=1, max_length=128)


class RetrievalHit(BaseModel):
    chunk_id: str
    document_id: str
    source_name: str | None = None
    team_id: str
    chunk_index: int
    content: str
    score: float


class RetrievalSearchResult(BaseModel):
    team_id: str
    user_id: str | None
    conversation_id: str | None
    query: str
    top_k: int
    embedding_model: str | None
    hits: list[RetrievalHit]
