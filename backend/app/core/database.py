from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from backend.app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    engine = create_async_engine(settings.database_url)
    if settings.database_url.startswith("sqlite"):
        event.listen(engine.sync_engine, "connect", _configure_sqlite)
    return engine


def _configure_sqlite(dbapi_connection: object, _connection_record: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()
