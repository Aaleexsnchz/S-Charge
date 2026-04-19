from uuid import UUID

from fastapi_users import schemas
from pydantic import field_validator


class UserRead(schemas.BaseUser[UUID]):
    name: str | None = None
    picture_url: str | None = None


class UserCreate(schemas.BaseUserCreate):
    name: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserUpdate(schemas.BaseUserUpdate):
    name: str | None = None
    picture_url: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value
