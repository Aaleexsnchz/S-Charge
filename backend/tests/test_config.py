import re
from pathlib import Path
from typing import Any

import pytest
from app.config import REQUIRED_IN_PRODUCTION, Settings
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"

# Set on containers by Compose, never read through Settings.
COMPOSE_ONLY_KEYS = frozenset(
    {"POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "SITE_ADDRESS"}
)

PRODUCTION: dict[str, Any] = {
    "environment": "production",
    "secret_key": "a-real-secret",
    "database_url": "postgresql+asyncpg://u:p@db:5432/d",
    "app_base_url": "https://example.test",
}


class IsolatedSettings(Settings):
    """Settings built only from explicit arguments.

    The ambient environment is a test input otherwise: CI exports a real
    `SECRET_KEY`, which would mask exactly the misconfiguration these tests
    assert the app refuses to boot on.
    """

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def setting_names() -> set[str]:
    return {
        field.validation_alias
        if isinstance(field.validation_alias, str)
        else name.upper()
        for name, field in Settings.model_fields.items()
    }


def documented_keys() -> set[str]:
    return {
        match.group(1)
        for line in ENV_EXAMPLE.read_text().splitlines()
        if (match := re.match(r"^([A-Z][A-Z0-9_]*)=", line))
    }


def test_every_setting_is_documented() -> None:
    """A setting absent from .env.example is a setting nobody sets on the server."""
    undocumented = setting_names() - documented_keys()

    assert not undocumented, f"missing from .env.example: {sorted(undocumented)}"


def test_no_documented_key_is_unused() -> None:
    stale = documented_keys() - setting_names() - COMPOSE_ONLY_KEYS

    assert not stale, f"documented but read by nothing: {sorted(stale)}"


@pytest.mark.parametrize("unconfigured", REQUIRED_IN_PRODUCTION)
def test_production_rejects_a_development_default(unconfigured: str) -> None:
    values = {**PRODUCTION, unconfigured: Settings.model_fields[unconfigured].default}

    with pytest.raises(ValueError, match=unconfigured):
        IsolatedSettings(**values)


def test_production_rejects_an_insecure_session_cookie() -> None:
    with pytest.raises(ValueError, match="SESSION_COOKIE_SECURE"):
        IsolatedSettings(**PRODUCTION, session_cookie_secure=False)


def test_production_requires_a_redirect_uri_once_google_is_configured() -> None:
    with pytest.raises(ValueError, match="google_redirect_uri"):
        IsolatedSettings(**PRODUCTION, google_client_id="a-client-id")


def test_production_accepts_a_complete_configuration() -> None:
    settings = IsolatedSettings(**PRODUCTION)

    assert settings.environment == "production"


def test_development_tolerates_the_shipped_defaults() -> None:
    settings = IsolatedSettings(environment="development")

    assert settings.secret_key == Settings.model_fields["secret_key"].default
