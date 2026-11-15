from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Must be set to something of their own in production. The check is equality
# with the declared default: a value still equal to it was never configured.
REQUIRED_IN_PRODUCTION = ("secret_key", "database_url", "app_base_url")

# Matches .env.example, so a copy of it left unedited is caught. A variable
# because ruff reads a literal assigned to `secret_key` as a credential (S105).
DEVELOPMENT_PLACEHOLDER = "change_me_secret_key"

# The fallback for an unstamped build, which the image passes in as an empty
# string rather than leaving the variable unset.
UNVERSIONED = "dev"


class Settings(BaseSettings):
    # Baked into the image at build time from the git tag. Never edit a version
    # string by hand: the tag is the source of truth (infra-0002).
    app_version: str = UNVERSIONED
    # `production` hides the OpenAPI docs and enables the checks below.
    environment: str = "development"
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

    ree_api_base_url: str = "https://apidatos.ree.es"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("app_version", mode="after")
    @classmethod
    def _treat_blank_as_unversioned(cls, value: str) -> str:
        return value or UNVERSIONED

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
