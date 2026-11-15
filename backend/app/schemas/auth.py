from typing import Annotated
from uuid import UUID

from fastapi_users import schemas
from pydantic import StringConstraints, field_validator

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
# Matches the column width, so an oversized value is a 422 rather than a 500.
PictureUrl = Annotated[str, StringConstraints(max_length=2048)]


class UserRead(schemas.BaseUser[UUID]):
    name: str | None = None
    picture_url: str | None = None


class UserCreate(schemas.BaseUserCreate):
    name: Name

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserUpdate(schemas.BaseUserUpdate):
    name: Name | None = None
    picture_url: PictureUrl | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value

    @field_validator("name")
    @classmethod
    def reject_null_name(cls, value: Name | None) -> Name:
        # Only runs when the caller sent the field: a PATCH omitting `name`
        # leaves it out of the update dict entirely.
        if value is None:
            raise ValueError("name cannot be cleared")
        return value
