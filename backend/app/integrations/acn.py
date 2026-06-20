import math
from typing import Any

import httpx

from app.config import settings
from app.utils.audit import audit


class AcnClient:
    """Async client for the ACN-Data sessions API (python-eve style).

    Auth is HTTP Basic with the API token as username and a blank password.
    Responses carry ``_items`` plus ``_meta`` (``page``, ``max_results``,
    ``total``); ``_meta`` is treated as optional so a schema drift downgrades
    to short-page detection instead of a crash.
    """

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        *,
        timeout: float = 60.0,
    ) -> None:
        key = token if token is not None else settings.acn_api_token
        url = base_url if base_url is not None else settings.acn_api_base_url
        if not key:
            raise RuntimeError("ACN_API_TOKEN is not set")
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/") + "/",
            auth=(key, ""),
            timeout=timeout,
        )

    async def __aenter__(self) -> "AcnClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_sessions(
        self,
        site: str,
        *,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[dict[str, Any]], int | None]:
        """Fetch one page of sessions for ``site``.

        Returns ``(items, total_pages)``; ``total_pages`` is ``None`` when the
        response carries no usable ``_meta``.
        """
        response = await self._client.get(
            f"sessions/{site}",
            params={"page": page, "max_results": per_page, "sort": "connectionTime"},
        )
        if response.is_error:
            audit(
                "acn_request_failed", site=site, page=page, status=response.status_code
            )
            response.raise_for_status()
        body = response.json()
        items: list[dict[str, Any]] = body.get("_items", [])
        meta = body.get("_meta") or {}
        total = meta.get("total")
        max_results = meta.get("max_results") or per_page
        total_pages = math.ceil(total / max_results) if isinstance(total, int) else None
        return items, total_pages
