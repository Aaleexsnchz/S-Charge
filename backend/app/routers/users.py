from fastapi import APIRouter

from app.schemas.auth import UserRead, UserUpdate
from app.services.user_manager import fastapi_users

router = APIRouter(prefix="/users", tags=["users"])

router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))
