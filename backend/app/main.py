from fastapi import FastAPI

from app.api.pokemon import router as pokemon_router
from app.api.types import router as types_router
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.api_name)
    app.state.backend_port = settings.backend_port

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(pokemon_router)
    app.include_router(types_router)
    return app


app = create_app()
