from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import init_db


class UTF8JSONResponse(JSONResponse):
    """Return JSON with explicit UTF-8 charset for Windows client compatibility."""

    media_type = "application/json; charset=utf-8"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Minimal enterprise IM AI CaiBao service.",
        lifespan=lifespan,
        default_response_class=UTF8JSONResponse,
    )

    app.include_router(api_router, prefix=settings.api_prefix)

    web_dir = Path(__file__).resolve().parent / "web"
    app.mount("/web", StaticFiles(directory=web_dir), name="web")

    @app.get("/", include_in_schema=False)
    def serve_frontend() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    return app


app = create_app()