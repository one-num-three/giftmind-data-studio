from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_secret: str
    team_passcode_hash: str
    database_url: str = "sqlite+aiosqlite:///./data/giftmind.sqlite3"
    data_dir: Path = Path("./data")
    upload_dir: Path = Path("./uploads")
    backup_dir: Path = Path("./backups")
    app_base_path: str = "/"
    schema_version: int = 1
    session_days: int = 7
    deepseek_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
