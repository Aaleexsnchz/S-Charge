from pathlib import Path
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "EV Charging API"
    environment: str = "development"
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    secret_key: str = "change_me_secret_key"

    # Database (async URL for runtime)
    database_url: str = (
        "postgresql+asyncpg://app_user:change_me_db_password@localhost:5432/app_db"
    )

    backend_env_file: ClassVar[Path] = Path(__file__).resolve().parents[1] / ".env"
    root_env_file: ClassVar[Path] = Path(__file__).resolve().parents[2] / ".env"
    env_file_path: ClassVar[Path] = (
        backend_env_file if backend_env_file.exists() else root_env_file
    )

    model_config = SettingsConfigDict(
        env_file=str(env_file_path),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
