from app.schemas.chat import ChatActionRequest, ChatActionResponse
from app.services.tool_service import ToolService
from app.services.user_service import UserService


class ActionChatService:
    def __init__(self, user_service: UserService, tool_service: ToolService) -> None:
        self.user_service = user_service
        self.tool_service = tool_service

    def execute(self, payload: ChatActionRequest) -> ChatActionResponse:
        self.user_service.ensure_user_in_team(
            user_id=payload.user_id,
            team_id=payload.team_id,
        )

        result = self.tool_service.execute(
            team_id=payload.team_id,
            user_id=payload.user_id,
            action=payload.action,
            arguments=payload.arguments,
        )

        return ChatActionResponse.from_result(
            user_id=payload.user_id,
            team_id=payload.team_id,
            conversation_id=payload.conversation_id,
            action=payload.action,
            result=result,
        )
