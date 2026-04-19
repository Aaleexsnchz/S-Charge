from fastapi import APIRouter

from app.schemas.auth import UserCreate, UserRead
from app.services.user_manager import fastapi_users
from app.utils.auth_backend import auth_backend

router = APIRouter(prefix="/auth", tags=["auth"])

router.include_router(fastapi_users.get_auth_router(auth_backend))
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))
