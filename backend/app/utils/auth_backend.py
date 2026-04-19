from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

from app.config import settings

ALGORITHM = "HS256"
TOKEN_AUDIENCE = ["tfm:session"]
COOKIE_NAME = "session"


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.secret_key,
        lifetime_seconds=settings.session_token_expire_days * 86400,
        algorithm=ALGORITHM,
        token_audience=TOKEN_AUDIENCE,
    )


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
