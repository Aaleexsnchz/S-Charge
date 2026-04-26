from fastapi import Response, status
from fastapi.responses import RedirectResponse
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

from app.config import settings

ALGORITHM = "HS256"
TOKEN_AUDIENCE = ["tfm:session"]
COOKIE_NAME = "session"
OAUTH_LOGIN_REDIRECT_URL = "/profile"

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

    Stock CookieTransport returns 204 No Content, which works for email/password
    (the frontend action handles the redirect) but leaves OAuth callbacks — a
    top-level browser navigation from the provider — on a blank page. Emitting
    a server-side 303 with Set-Cookie avoids a popup-based frontend flow that
    would be fragile on installed PWAs (see slice 3).
    """

    def __init__(self, login_redirect_url: str, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.login_redirect_url = login_redirect_url

    async def get_login_response(self, token: str) -> Response:
        response = RedirectResponse(self.login_redirect_url, status_code=status.HTTP_303_SEE_OTHER)
        return self._set_login_cookie(response, token)


cookie_transport = CookieTransport(
    cookie_name=COOKIE_NAME,
    cookie_max_age=_SESSION_SECONDS,
    cookie_secure=settings.session_cookie_secure,
    cookie_httponly=True,
    cookie_samesite="lax",
)

oauth_cookie_transport = CookieRedirectTransport(
    login_redirect_url=OAUTH_LOGIN_REDIRECT_URL,
    cookie_name=COOKIE_NAME,
    cookie_max_age=_SESSION_SECONDS,
    cookie_secure=settings.session_cookie_secure,
    cookie_httponly=True,
    cookie_samesite="lax",
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
