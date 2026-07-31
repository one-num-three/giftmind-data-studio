from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import api_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.database import create_engine
from backend.app.services.taobao_login import TaobaoLoginManager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    engine = create_engine(resolved)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    taobao_login = TaobaoLoginManager(resolved.taobao_state_path, resolved.playwright_timeout_ms)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved.data_dir.mkdir(parents=True, exist_ok=True)
        yield
        await taobao_login.close()
        await engine.dispose()

    app = FastAPI(title="GiftMind Data Studio", lifespan=lifespan)
    app.state.settings = resolved
    app.state.session_factory = session_factory
    app.state.taobao_login = taobao_login
    app.include_router(api_router)
    resolved.upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=resolved.upload_dir), name="uploads")

    @app.get("/api/health")
    async def health() -> dict[str, str | int]:
        return {"status": "ok", "schemaVersion": resolved.schema_version}

    return app

app = create_app()
