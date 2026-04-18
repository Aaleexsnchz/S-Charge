from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # TODO: wire into prod/dev branching (CORS, /docs visibility) at Phase 6 deploy
    environment: str = "development"
    # TODO: pass to FastAPI(debug=...) or gate verbose SQL logging when needed
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    # TODO: use for JWT signing in Phase 1 auth; replace default before prod
    secret_key: str = "change_me_secret_key"
    database_url: str = "postgresql+asyncpg://app_user:change_me_db_password@localhost:5432/app_db"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
