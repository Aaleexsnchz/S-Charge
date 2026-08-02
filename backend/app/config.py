from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Must be set to something of their own in production. The check is equality
# with the declared default: a value still equal to it was never configured.
REQUIRED_IN_PRODUCTION = ("secret_key", "database_url", "app_base_url")

# The literal .env.example ships, so copying that file without editing it is
# caught. Held in a variable rather than inline because ruff reads a string
# literal assigned to `secret_key` as a hardcoded credential (S105).
DEVELOPMENT_PLACEHOLDER = "change_me_secret_key"


class Settings(BaseSettings):
    # Baked into the image at build time from the git tag; `dev` everywhere the
    # image was not built by CD. Never edit a version string by hand.
    app_version: str = "dev"
    # TODO: wire into /docs visibility when needed; it already gates the
    # production configuration check below.
    environment: str = "development"
    # TODO: pass to FastAPI(debug=...) or gate verbose SQL logging when needed
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    secret_key: str = DEVELOPMENT_PLACEHOLDER
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

    @model_validator(mode="after")
    def _reject_development_defaults_in_production(self) -> Self:
        """Fail the boot rather than serve production with a development config.

        Without this the app starts happily on `secret_key = ""`, signing every
        session cookie and password-reset token with a value an attacker knows.
        """
        if self.environment != "production":
            return self

        defaults = type(self).model_fields
        unset = [
            name
            for name in REQUIRED_IN_PRODUCTION
            if not getattr(self, name) or getattr(self, name) == defaults[name].default
        ]
        if self.google_client_id and (
            self.google_redirect_uri == defaults["google_redirect_uri"].default
        ):
            unset.append("google_redirect_uri")

        problems = []
        if unset:
            problems.append(
                f"unset or still at the development default: {', '.join(sorted(unset))}"
            )
        if not self.session_cookie_secure:
            problems.append(
                "SESSION_COOKIE_SECURE is false, so sessions would ride plain HTTP"
            )
        if problems:
            raise ValueError(f"ENVIRONMENT=production but {'; '.join(problems)}")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
