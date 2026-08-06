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
from app.services.email import send_reset_password_email, send_verification_email
from app.utils.audit import audit
from app.utils.auth_backend import auth_backend
from app.utils.security import password_helper

# NIST SP 800-63B-4 §3.1.1 requires 15 for a password used as a single factor, which is
# this case. Eight would be permissible only as part of multi-factor authentication.
MIN_PASSWORD_LENGTH = 15
PASSWORD_PROVIDER = "password"  # noqa: S105 — login-provider name, not a credential


def _detect_provider(request: Request | None) -> str:
    """Derive the login provider from the matched fastapi-users route name.

    fastapi-users names its OAuth callback route
    `oauth:{client.name}.{backend.name}.callback` (see fastapi_users/router/oauth.py).
    The email/password login route has no such prefix, so a missing or non-oauth
    route name means password login.
    """
    if request is None:
        return PASSWORD_PROVIDER
    route = request.scope.get("route")
    route_name = getattr(route, "name", "") or ""
    if not route_name.startswith("oauth:"):
        return PASSWORD_PROVIDER
    return route_name.removeprefix("oauth:").split(".", 1)[0]


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def validate_password(self, password: str, user: Any) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordException(
                reason=f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )

    async def on_after_register(
        self, user: User, request: Request | None = None
    ) -> None:
        audit(
            "register",
            user_id=str(user.id),
            email=user.email,
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
        if not user.is_verified:
            await self.request_verify(user, request)

    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response: Any = None,
    ) -> None:
        audit(
            "login_ok",
            user_id=str(user.id),
            provider=_detect_provider(request),
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        await send_verification_email(user.email, token)

    async def on_after_verify(self, user: User, request: Request | None = None) -> None:
        audit(
            "verify_ok",
            user_id=str(user.id),
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        await send_reset_password_email(user.email, token)

    async def on_after_reset_password(
        self, user: User, request: Request | None = None
    ) -> None:
        audit(
            "reset_ok",
            user_id=str(user.id),
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

    async def oauth_callback(  # type: ignore[override]
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: str,
        expires_at: int | None = None,
        refresh_token: str | None = None,
        request: Request | None = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> User:
        user = await super().oauth_callback(  # type: ignore[attr-defined]
            oauth_name,
            access_token,
            account_id,
            account_email,
            expires_at,
            refresh_token,
            request,
            associate_by_email=associate_by_email,
            is_verified_by_default=is_verified_by_default,
        )
        if not user.is_verified:
            new_hash = self.password_helper.hash(self.password_helper.generate())
            user = await self.user_db.update(
                user, {"is_verified": True, "hashed_password": new_hash}
            )
            audit(
                "oauth_link_reset_password",
                user_id=str(user.id),
                email=user.email,
                oauth_name=oauth_name,
            )
        return user


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase, Depends(get_user_db)],
) -> AsyncIterator[UserManager]:
    yield UserManager(user_db, password_helper)


fastapi_users = FastAPIUsers[User, UUID](get_user_manager, [auth_backend])
current_user = fastapi_users.current_user(active=True)
