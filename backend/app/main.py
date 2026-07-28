from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.router import api_router
from backend.app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved.data_dir.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(title="GiftMind Data Studio", lifespan=lifespan)
    app.state.settings = resolved
    app.include_router(api_router)

    @app.get("/api/health")
    async def health() -> dict[str, str | int]:
        return {"status": "ok", "schemaVersion": resolved.schema_version}

    return app

app = create_app()
