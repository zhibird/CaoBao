from pydantic import BaseModel, Field


class LibraryPublishRequest(BaseModel):
    team_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    document_id: str = Field(min_length=1, max_length=36)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=36)
    space_id: str | None = Field(default=None, min_length=1, max_length=36)
    source_name: str | None = Field(default=None, min_length=1, max_length=255)
