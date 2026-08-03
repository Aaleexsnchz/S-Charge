from fastapi import APIRouter, Depends
from httpx_oauth.clients.google import GoogleOAuth2

from app.config import settings
from app.schemas.auth import UserCreate, UserRead
from app.services.user_manager import fastapi_users
from app.utils.auth_backend import auth_backend, oauth_backend
from app.utils.rate_limit import rate_limit

# Per IP and per path, so /login and /logout hold separate counters even though
# one dependency covers both. Endpoints that send mail are limited by the hour
# because their cost is somebody else's inbox, not this server's CPU.
LOGIN_LIMIT = "10/minute"
REGISTER_LIMIT = "10/hour"
MAIL_LIMIT = "5/hour"

router = APIRouter(prefix="/auth", tags=["auth"])

router.include_router(
    fastapi_users.get_auth_router(auth_backend, requires_verification=True),
    dependencies=[Depends(rate_limit(LOGIN_LIMIT))],
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    dependencies=[Depends(rate_limit(REGISTER_LIMIT))],
)
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    dependencies=[Depends(rate_limit(MAIL_LIMIT))],
)
router.include_router(
    fastapi_users.get_reset_password_router(),
    dependencies=[Depends(rate_limit(MAIL_LIMIT))],
)

google_client = GoogleOAuth2(settings.google_client_id, settings.google_client_secret)

router.include_router(
    fastapi_users.get_oauth_router(
        google_client,
        oauth_backend,
        settings.secret_key,
        redirect_url=settings.google_redirect_uri,
        associate_by_email=True,
        is_verified_by_default=True,
    ),
    prefix="/google",
)
