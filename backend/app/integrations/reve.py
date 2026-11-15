"""Client for the REVE external API v1.

Vendored spec: docs/reve-api-spec.json. Two constraints from it shape everything
here: 5 requests per hour per API key, and `limit` capped at 100.
"""

import asyncio
from http import HTTPStatus
from typing import Any

import httpx

from app.config import settings
from app.utils.audit import audit

TRANSIENT_STATUS = frozenset(
    {
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    }
)
SERVER_STATUS = TRANSIENT_STATUS - {HTTPStatus.TOO_MANY_REQUESTS}


def is_rate_limit(exc: Exception) -> bool:
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    )


def is_server_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code in SERVER_STATUS
    )


class ReveClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        timeout: float = 30.0,
        max_retry_delay: float = 30.0,
        max_retries: int = 1,
    ) -> None:
        key = api_key if api_key is not None else settings.reve_api_key
        url = base_url if base_url is not None else settings.reve_api_base_url
        if not key:
            raise RuntimeError("REVE_API_KEY is not set")
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/") + "/",
            headers={"x-api-key": key},
            timeout=timeout,
        )
        self._max_retry_delay = max_retry_delay
        self._max_retries = max_retries

    async def __aenter__(self) -> "ReveClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        target = path.lstrip("/")
        attempt = 0
        while True:
            try:
                response = await self._client.get(target, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt >= self._max_retries:
                    audit("reve_request_failed", path=path, error=type(exc).__name__)
                    raise
                delay = self._backoff_seconds(attempt)
                audit(
                    "reve_transient_retry",
                    path=path,
                    error=type(exc).__name__,
                    delay=delay,
                )
                await asyncio.sleep(delay)
                attempt += 1
                continue

            if response.status_code in TRANSIENT_STATUS and attempt < self._max_retries:
                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    delay = self._retry_after_seconds(response)
                    audit("reve_rate_limited_retry", path=path, delay=delay)
                else:
                    delay = self._backoff_seconds(attempt)
                    audit(
                        "reve_transient_retry",
                        path=path,
                        status=response.status_code,
                        delay=delay,
                    )
                await asyncio.sleep(delay)
                attempt += 1
                continue

            if response.is_error:
                audit("reve_request_failed", path=path, status=response.status_code)
                response.raise_for_status()
            return response.json()

    def _retry_after_seconds(self, response: httpx.Response) -> float:
        header = response.headers.get("Retry-After")
        if not header:
            return 2.0
        try:
            return min(float(header), self._max_retry_delay)
        except ValueError:
            return 2.0

    def _backoff_seconds(self, attempt: int) -> float:
        return min(2.0 * (2**attempt), self._max_retry_delay)
