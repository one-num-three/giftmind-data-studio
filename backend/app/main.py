from fastapi import FastAPI
from pydantic import ValidationError

from backend.app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(title="GiftMind Data Studio")
    app.state.settings = resolved

    @app.get("/api/health")
    async def health() -> dict[str, str | int]:
        return {"status": "ok", "schemaVersion": resolved.schema_version}

    return app


try:
    app = create_app()
except ValidationError:
    app = create_app(Settings(app_secret="", team_passcode_hash=""))
