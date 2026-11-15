from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse, Response

from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.points import router as points_router
from app.routers.prices import router as prices_router
from app.routers.simulate import router as simulate_router
from app.routers.users import router as users_router
from app.routers.vehicles import router as vehicles_router
from app.schemas.health import HealthRead
from app.services.user_manager import current_user

OAUTH_PATH_PREFIX = "/api/auth/google/"
OAUTH_FAILURE_REDIRECT = "/login?error=oauth_failed"


# Dropping the schema route takes Swagger and ReDoc with it: FastAPI mounts both
# only `if self.openapi_url`. `just gen-api` calls app.openapi() directly rather
# than over HTTP, so the committed contract is unaffected.
app = FastAPI(
    title="EV Charging Point Management API",
    version=settings.app_version,
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)

app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_allow_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def oauth_redirect_exception_handler(
    request: Request, exc: HTTPException
) -> Response:
    is_oauth_path = request.url.path.startswith(OAUTH_PATH_PREFIX)
    if is_oauth_path and exc.status_code == status.HTTP_400_BAD_REQUEST:
        return RedirectResponse(
            OAUTH_FAILURE_REDIRECT, status_code=status.HTTP_303_SEE_OTHER
        )
    return await http_exception_handler(request, exc)


app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")

# Every data endpoint requires a session, as every page does in the frontend.
# Applied at the mount rather than per route, so a new endpoint inside one of
# these routers cannot be added unguarded.
AUTHENTICATED = [Depends(current_user)]

app.include_router(points_router, prefix="/api", dependencies=AUTHENTICATED)
app.include_router(prices_router, prefix="/api", dependencies=AUTHENTICATED)
app.include_router(simulate_router, prefix="/api", dependencies=AUTHENTICATED)
app.include_router(vehicles_router, prefix="/api", dependencies=AUTHENTICATED)


@app.get("/api/health")
async def health() -> HealthRead:
    return HealthRead(status="ok", version=settings.app_version)
