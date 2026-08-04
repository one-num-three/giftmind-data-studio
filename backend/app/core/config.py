from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    # Full H5 plans are substantially larger than single-field suggestions.
    # One patient request avoids cancelling and restarting the same generation.
    deepseek_timeout_seconds: float = Field(default=120, gt=0, le=300)
    deepseek_max_retries: int = Field(default=0, ge=0, le=5)
    vision_api_key: str | None = None
    vision_base_url: str | None = None
    vision_model: str | None = None
    playwright_enabled: bool = True
    playwright_timeout_ms: int = Field(default=20_000, ge=5_000, le=60_000)
    taobao_state_path: Path = Path("./data/private/taobao-state.json")

    @field_validator("app_secret", "team_passcode")
    @classmethod
    def require_nonblank_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("deepseek_base_url", "deepseek_model")
    @classmethod
    def require_nonblank_deepseek_setting(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


@lru_cache
def get_settings() -> Settings:
    return Settings()
