from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.conversation import router as conversation_router
from app.api.routes.document import router as document_router
from app.api.routes.health import router as health_router
from app.api.routes.llm_model import router as llm_model_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.team import router as team_router
from app.api.routes.user import router as user_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(team_router, tags=["teams"])
api_router.include_router(user_router, tags=["users"])
api_router.include_router(conversation_router, tags=["conversations"])
api_router.include_router(llm_model_router, tags=["llm-models"])
api_router.include_router(document_router, tags=["documents"])
api_router.include_router(retrieval_router, tags=["retrieval"])
api_router.include_router(chat_router, tags=["chat"])
