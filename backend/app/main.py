from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.battle import battle_session_router, router as battle_router
from app.api.pokemon import router as pokemon_router
from app.api.recognition import router as recognition_router
from app.api.types import router as types_router
from app.api.video import router as video_router
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.api_name)
    app.state.backend_port = settings.backend_port

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(battle_router)
    app.include_router(battle_session_router)
    app.include_router(pokemon_router)
    app.include_router(types_router)
    app.include_router(video_router)
    app.include_router(recognition_router)
    return app


app = create_app()
