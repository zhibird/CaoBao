from app.schemas.chat import ChatEchoRequest, ChatEchoResponse
from app.services.user_service import UserService


class ChatService:
    """Service layer for chat-related business logic."""

    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    def echo(self, payload: ChatEchoRequest) -> ChatEchoResponse:
        self.user_service.ensure_user_in_team(
            user_id=payload.user_id,
            team_id=payload.team_id,
        )

        answer = f"[Echo] {payload.message}"
        return ChatEchoResponse.from_message(
            user_id=payload.user_id,
            team_id=payload.team_id,
            answer=answer,
        )
