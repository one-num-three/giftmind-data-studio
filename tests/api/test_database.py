import asyncio

from sqlalchemy import text

from backend.app.core.config import Settings
from backend.app.core.database import create_engine


def test_sqlite_engine_enables_required_pragmas(tmp_path):
    database_path = tmp_path / "giftmind.sqlite3"
    settings = Settings(
        app_secret="",
        team_passcode="",
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )

    async def read_pragmas() -> tuple[int, str, int]:
        engine = create_engine(settings)
        try:
            async with engine.connect() as connection:
                foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar_one()
                journal_mode = (await connection.execute(text("PRAGMA journal_mode"))).scalar_one()
                busy_timeout = (await connection.execute(text("PRAGMA busy_timeout"))).scalar_one()
            return foreign_keys, journal_mode, busy_timeout
        finally:
            await engine.dispose()

    assert asyncio.run(read_pragmas()) == (1, "wal", 5000)
