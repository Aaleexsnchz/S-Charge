from fastapi import APIRouter
from httpx_oauth.clients.google import GoogleOAuth2

from app.config import settings
from app.schemas.auth import UserCreate, UserRead
from app.services.user_manager import fastapi_users
from app.utils.auth_backend import auth_backend, oauth_backend

router = APIRouter(prefix="/auth", tags=["auth"])

router.include_router(
    fastapi_users.get_auth_router(auth_backend, requires_verification=True)
)
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))
router.include_router(fastapi_users.get_verify_router(UserRead))
router.include_router(fastapi_users.get_reset_password_router())

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
