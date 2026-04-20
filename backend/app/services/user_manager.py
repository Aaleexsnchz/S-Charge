from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.exceptions import InvalidPasswordException

from app.config import settings
from app.dependencies import get_user_db
from app.models.user import User
from app.utils.audit import audit
from app.utils.auth_backend import auth_backend
from app.utils.security import password_helper

MIN_PASSWORD_LENGTH = 12


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def validate_password(self, password: str, user: Any) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordException(
                reason=f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        audit(
            "register",
            user_id=str(user.id),
            email=user.email,
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response: Any = None,
    ) -> None:
        audit(
            "login_ok",
            user_id=str(user.id),
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase, Depends(get_user_db)],
) -> AsyncIterator[UserManager]:
    yield UserManager(user_db, password_helper)


fastapi_users = FastAPIUsers[User, UUID](get_user_manager, [auth_backend])
current_user = fastapi_users.current_user(active=True)
