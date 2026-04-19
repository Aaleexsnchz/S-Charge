from fastapi_users.authentication import AuthenticationBackend, CookieTransport

from app.config import settings
from app.utils.jwt_strategy import get_jwt_strategy

COOKIE_NAME = "session"

cookie_transport = CookieTransport(
    cookie_name=COOKIE_NAME,
    cookie_max_age=settings.session_token_expire_days * 86400,
    cookie_secure=settings.session_cookie_secure,
    cookie_httponly=True,
    cookie_samesite="lax",
)

auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
