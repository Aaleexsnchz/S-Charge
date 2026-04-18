from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # TODO: wire into prod/dev branching (CORS, /docs visibility) at Phase 6 deploy
    environment: str = "development"
    # TODO: pass to FastAPI(debug=...) or gate verbose SQL logging when needed
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    # Reused as the HMAC signing key for both access and refresh JWTs (see auth-decisions §4).
    secret_key: str = "change_me_secret_key"
    database_url: str = "postgresql+asyncpg://app_user:change_me_db_password@localhost:5432/app_db"

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_secure: bool = True
    refresh_cookie_path: str = "/auth/refresh"

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
