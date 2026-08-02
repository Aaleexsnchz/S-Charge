from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # TODO: wire into prod/dev branching (/docs visibility) when needed
    environment: str = "development"
    # TODO: pass to FastAPI(debug=...) or gate verbose SQL logging when needed
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    secret_key: str = ""
    # Comma-separated. Prod is same-origin behind Caddy, so it sets this empty.
    cors_allow_origins: str = "http://localhost:5173"
    database_url: str = (
        "postgresql+asyncpg://app_user:change_me_db_password@localhost:5432/app_db"
    )
    test_database_url: str = (
        "postgresql+asyncpg://app_user:change_me_db_password@localhost:5432/app_db_test"
    )

    session_token_expire_days: int = 14
    session_cookie_secure: bool = True

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5173/api/auth/google/callback"

    resend_api_key: str = ""
    mail_from: str = "onboarding@resend.dev"
    app_base_url: str = "http://localhost:5173"

    reve_api_key: str = ""
    reve_api_base_url: str = "https://www.mapareve.es/api/external/v1"
    reve_budget_per_run: int = 5
    reve_refresh_lookback_hours: int = 2

    ree_api_base_url: str = "https://apidatos.ree.es"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
