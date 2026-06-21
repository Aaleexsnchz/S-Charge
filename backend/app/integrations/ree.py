from datetime import date, datetime
from decimal import Decimal
from http import HTTPStatus
from typing import Any

import httpx

from app.config import settings
from app.utils.audit import audit

PVPC_INDICATOR_ID = "1001"
PRICES_PATH = "/es/datos/mercados/precios-mercados-tiempo-real"


class ReeClient:
    """Async client for REE's public data API (apidatos.ree.es, no auth).

    The real-time market prices endpoint returns a JSON:API-style payload;
    the PVPC series is the ``included`` entry with id 1001, values in €/MWh.
    """

    def __init__(self, base_url: str | None = None, *, timeout: float = 30.0) -> None:
        url = base_url if base_url is not None else settings.ree_api_base_url
        self._client = httpx.AsyncClient(base_url=url.rstrip("/"), timeout=timeout)

    async def __aenter__(self) -> "ReeClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_pvpc_prices(self, day: date) -> list[tuple[datetime, Decimal]]:
        """Hourly PVPC prices for ``day`` as ``(hour_start, €/kWh)`` tuples.

        Returns an empty list when REE has not published the day yet
        (tomorrow's prices appear around 20:15 CET).
        """
        params = {
            "start_date": f"{day.isoformat()}T00:00",
            "end_date": f"{day.isoformat()}T23:59",
            "time_trunc": "hour",
        }
        response = await self._client.get(PRICES_PATH, params=params)
        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            # REE answers 500 for days it has not published yet (e.g. tomorrow
            # before ~20:15 CET) — treat as "no data", not as a hard failure.
            audit(
                "ree_day_not_published",
                day=day.isoformat(),
                status=response.status_code,
            )
            return []
        if response.is_error:
            audit(
                "ree_request_failed", day=day.isoformat(), status=response.status_code
            )
            response.raise_for_status()
        body = response.json()

        series = self._pvpc_series(body)
        if series is None:
            audit("ree_pvpc_series_missing", day=day.isoformat())
            return []

        prices: list[tuple[datetime, Decimal]] = []
        for value in series.get("attributes", {}).get("values", []):
            hour_start = datetime.fromisoformat(value["datetime"])
            price_per_kwh = Decimal(str(value["value"])) / 1000
            prices.append((hour_start, price_per_kwh))
        return prices

    @staticmethod
    def _pvpc_series(body: dict[str, Any]) -> dict[str, Any] | None:
        for entry in body.get("included") or []:
            if entry.get("id") == PVPC_INDICATOR_ID:
                return entry
            title = str(entry.get("attributes", {}).get("title", ""))
            if title.upper().startswith("PVPC"):
                return entry
        return None
