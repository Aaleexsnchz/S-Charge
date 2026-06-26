from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse, Response

from app.routers.auth import router as auth_router
from app.routers.points import router as points_router
from app.routers.prices import router as prices_router
from app.routers.simulate import router as simulate_router
from app.routers.users import router as users_router
from app.routers.vehicles import router as vehicles_router

OAUTH_PATH_PREFIX = "/api/auth/google/"
OAUTH_FAILURE_REDIRECT = "/login?error=oauth_failed"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(
    title="EV Charging Point Management API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
app.include_router(points_router, prefix="/api")
app.include_router(prices_router, prefix="/api")
app.include_router(simulate_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(vehicles_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
