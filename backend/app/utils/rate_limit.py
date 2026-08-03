import math
import time
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status
from limits import parse
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter

# In-process storage, so the counters are per container and reset on restart.
# Correct only while the backend runs a single uvicorn worker; more than one
# would give each its own counters and multiply every limit below.
_storage = MemoryStorage()
_limiter = MovingWindowRateLimiter(_storage)

UNKNOWN_CLIENT = "unknown"


def _client_key(request: Request) -> str:
    """Identify the caller by IP.

    Behind Caddy this is only the real client because the proxy overwrites
    `X-Forwarded-For` and uvicorn is told to trust the Docker network; without
    both, every caller shares one bucket and one attacker throttles everyone.
    """
    return request.client.host if request.client else UNKNOWN_CLIENT


def rate_limit(limit: str) -> Callable[[Request], Awaitable[None]]:
    item = parse(limit)

    async def dependency(request: Request) -> None:
        key = _client_key(request)
        if await _limiter.hit(item, request.url.path, key):
            return

        stats = await _limiter.get_window_stats(item, request.url.path, key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="TOO_MANY_REQUESTS",
            headers={
                "Retry-After": str(max(1, math.ceil(stats.reset_time - time.time())))
            },
        )

    return dependency


async def reset_rate_limits() -> None:
    """Drop every counter. For tests, which would otherwise leak state."""
    await _storage.reset()
