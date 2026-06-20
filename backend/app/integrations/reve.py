import asyncio
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any

import httpx

from app.config import settings
from app.utils.audit import audit

MAX_PAGE_SIZE = 100


class ReveClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        timeout: float = 30.0,
        max_retry_delay: float = 30.0,
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

    async def __aenter__(self) -> "ReveClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._client.get(path.lstrip("/"), params=params)
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            delay = self._retry_after_seconds(response)
            audit("reve_rate_limited_retry", path=path, delay=delay)
            await asyncio.sleep(delay)
            response = await self._client.get(path.lstrip("/"), params=params)
        if response.is_error:
            audit("reve_request_failed", path=path, status=response.status_code)
            response.raise_for_status()
        return response.json()

    async def get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        data_key: str | None = None,
        page_size: int = MAX_PAGE_SIZE,
    ) -> AsyncIterator[dict[str, Any]]:
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValueError(
                f"REVE caps limit between 1 and {MAX_PAGE_SIZE}; got {page_size}"
            )
        page = 1
        while True:
            page_params = {**(params or {}), "page": page, "limit": page_size}
            response = await self.get(path, params=page_params)
            items = response[data_key] if data_key else response
            if not items:
                return
            for item in items:
                yield item
            if len(items) < page_size:
                return
            page += 1

    def _retry_after_seconds(self, response: httpx.Response) -> float:
        header = response.headers.get("Retry-After")
        if not header:
            return 2.0
        try:
            return min(float(header), self._max_retry_delay)
        except ValueError:
            return 2.0
