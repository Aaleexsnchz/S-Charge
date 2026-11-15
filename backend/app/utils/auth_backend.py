from typing import Any

from fastapi import Response, status
from fastapi.responses import RedirectResponse
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)

from app.config import settings

ALGORITHM = "HS256"
TOKEN_AUDIENCE = ["s-charge:session"]
COOKIE_NAME = "session"
OAUTH_LOGIN_REDIRECT_URL = "/"

_SESSION_SECONDS = settings.session_token_expire_days * 86400


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.secret_key,
        lifetime_seconds=_SESSION_SECONDS,
        algorithm=ALGORITHM,
        token_audience=TOKEN_AUDIENCE,
    )


class CookieRedirectTransport(CookieTransport):
    """CookieTransport variant that 303s to a frontend URL after login.

    Stock CookieTransport answers 204, which suits the email/password form but
    leaves an OAuth callback, a top-level navigation from the provider, on a
    blank page. A server-side 303 with Set-Cookie avoids a popup-based flow,
    which is fragile on installed PWAs.
    """

    def __init__(self, login_redirect_url: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.login_redirect_url = login_redirect_url

    async def get_login_response(self, token: str) -> Response:
        response = RedirectResponse(
            self.login_redirect_url, status_code=status.HTTP_303_SEE_OTHER
        )
        return self._set_login_cookie(response, token)


_COOKIE_SETTINGS: dict[str, Any] = {
    "cookie_name": COOKIE_NAME,
    "cookie_max_age": _SESSION_SECONDS,
    "cookie_secure": settings.session_cookie_secure,
    "cookie_httponly": True,
    "cookie_samesite": "lax",
}

cookie_transport = CookieTransport(**_COOKIE_SETTINGS)

oauth_cookie_transport = CookieRedirectTransport(
    login_redirect_url=OAUTH_LOGIN_REDIRECT_URL, **_COOKIE_SETTINGS
)

auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

oauth_backend = AuthenticationBackend(
    name="oauth-cookie",
    transport=oauth_cookie_transport,
    get_strategy=get_jwt_strategy,
)
