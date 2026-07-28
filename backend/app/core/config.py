from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_secret: str
    team_passcode: str
    database_url: str = "sqlite+aiosqlite:///./data/giftmind.sqlite3"
    data_dir: Path = Path("./data")
    upload_dir: Path = Path("./uploads")
    backup_dir: Path = Path("./backups")
    app_base_path: str = "/"
    schema_version: int = 1
    deepseek_api_key: str | None = None
    vision_api_key: str | None = None
    vision_base_url: str | None = None
    vision_model: str | None = None

    @field_validator("app_secret", "team_passcode")
    @classmethod
    def require_nonblank_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
