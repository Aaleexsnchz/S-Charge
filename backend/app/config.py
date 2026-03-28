from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://tfm:tfm_secret@localhost:5432/ev_charging"
    secret_key: str = "change-me-in-production"

    model_config = {"env_file": ".env"}


settings = Settings()
