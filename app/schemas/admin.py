from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class AdminSessionResponse(BaseModel):
    account_id: str
    team_id: str
    display_name: str
    role: str
    authenticated_at: str

    @classmethod
    def from_account(
        cls,
        *,
        account_id: str,
        team_id: str,
        display_name: str,
        role: str,
    ) -> "AdminSessionResponse":
        return cls(
            account_id=account_id,
            team_id=team_id,
            display_name=display_name,
            role=role,
            authenticated_at=datetime.now(timezone.utc).isoformat(),
        )


class AdminDashboardResponse(BaseModel):
    teams: int
    users: int
    conversations: int
    documents: int
    messages: int


class AdminTeamItem(BaseModel):
    team_id: str
    name: str
    description: str | None
    created_at: datetime
    user_count: int = 0
    conversation_count: int = 0
    document_count: int = 0


class AdminUserItem(BaseModel):
    user_id: str
    team_id: str
    display_name: str
    role: str
    created_at: datetime
    conversation_count: int = 0
    document_count: int = 0


class AdminUserRoleUpdate(BaseModel):
    role: str = Field(min_length=1, max_length=32)


class AdminConversationItem(BaseModel):
    conversation_id: str
    team_id: str
    user_id: str
    title: str
    status: str
    is_pinned: bool
    created_at: datetime
    message_count: int = 0
    document_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AdminDocumentItem(BaseModel):
    document_id: str
    team_id: str
    conversation_id: str | None
    source_name: str
    content_type: str
    status: str
    created_at: datetime
    char_count: int = 0
    content_preview: str = ""

    model_config = ConfigDict(from_attributes=True)


class AdminDocumentDetail(AdminDocumentItem):
    content: str
