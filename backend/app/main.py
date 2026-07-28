from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.app.api.router import api_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.database import create_engine
from backend.app.models.operations import Base


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved.data_dir.mkdir(parents=True, exist_ok=True)
        engine = create_engine(resolved)
        app.state.engine = engine
        app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="GiftMind Data Studio", lifespan=lifespan)
    app.state.settings = resolved
    app.state.failed_logins: defaultdict[str, deque[datetime]] = defaultdict(deque)
    app.include_router(api_router)

    @app.get("/api/health")
    async def health() -> dict[str, str | int]:
        return {"status": "ok", "schemaVersion": resolved.schema_version}

    return app

app = create_app()
