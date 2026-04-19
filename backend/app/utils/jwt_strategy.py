from fastapi_users.authentication import JWTStrategy

from app.config import settings

ALGORITHM = "HS256"
TOKEN_AUDIENCE = ["tfm:session"]


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.secret_key,
        lifetime_seconds=settings.session_token_expire_days * 86400,
        algorithm=ALGORITHM,
        token_audience=TOKEN_AUDIENCE,
    )
