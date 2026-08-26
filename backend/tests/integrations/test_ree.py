from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.integrations.ree import ReeClient
from pytest_httpx import HTTPXMock

BASE_URL = "https://ree.test"
DAY_URL = (
    f"{BASE_URL}/es/datos/mercados/precios-mercados-tiempo-real"
    "?start_date=2026-06-12T00%3A00&end_date=2026-06-12T23%3A59&time_trunc=hour"
)


async def test_parses_pvpc_series_and_converts_units(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=DAY_URL,
        json={
            "included": [
                {
                    "id": "600",
                    "attributes": {"title": "Precio mercado spot", "values": []},
                },
                {
                    "id": "1001",
                    "attributes": {
                        "title": "PVPC",
                        "values": [
                            {
                                "value": 85.21,
                                "datetime": "2026-06-12T00:00:00.000+02:00",
                            },
                            {
                                "value": 272.2,
                                "datetime": "2026-06-12T21:00:00.000+02:00",
                            },
                        ],
                    },
                },
            ]
        },
    )

    async with ReeClient(base_url=BASE_URL) as client:
        prices = (await client.get_pvpc_prices(date(2026, 6, 12))).prices

    assert len(prices) == 2
    first_hour, first_price = prices[0]
    assert first_hour == datetime(
        2026, 6, 12, 0, 0, tzinfo=timezone(timedelta(hours=2))
    )
    assert first_price == Decimal("0.08521")
    assert prices[1][1] == Decimal("0.2722")


async def test_missing_pvpc_series_returns_empty(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=DAY_URL,
        json={
            "included": [{"id": "600", "attributes": {"title": "Spot", "values": []}}]
        },
    )

    async with ReeClient(base_url=BASE_URL) as client:
        assert (await client.get_pvpc_prices(date(2026, 6, 12))).prices == []


async def test_unpublished_day_500_returns_empty(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=DAY_URL, status_code=500)

    async with ReeClient(base_url=BASE_URL) as client:
        assert (await client.get_pvpc_prices(date(2026, 6, 12))).prices == []


async def test_captures_ree_publication_time(httpx_mock: HTTPXMock) -> None:
    """REE restates days it has already published, so its own write time is the
    only signal that a stored day has been superseded."""
    httpx_mock.add_response(
        url=DAY_URL,
        json={
            "included": [
                {
                    "id": "1001",
                    "attributes": {
                        "title": "PVPC",
                        "last-update": "2026-06-11T20:46:38.000+02:00",
                        "values": [
                            {
                                "value": 85.21,
                                "datetime": "2026-06-12T00:00:00.000+02:00",
                            }
                        ],
                    },
                }
            ]
        },
    )

    async with ReeClient(BASE_URL) as client:
        series = await client.get_pvpc_prices(date(2026, 6, 12))

    assert series.last_update == datetime(
        2026, 6, 11, 20, 46, 38, tzinfo=timezone(timedelta(hours=2))
    )
    assert len(series.prices) == 1


async def test_missing_publication_time_is_not_fatal(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=DAY_URL,
        json={
            "included": [
                {
                    "id": "1001",
                    "attributes": {
                        "title": "PVPC",
                        "values": [
                            {
                                "value": 85.21,
                                "datetime": "2026-06-12T00:00:00.000+02:00",
                            }
                        ],
                    },
                }
            ]
        },
    )

    async with ReeClient(BASE_URL) as client:
        series = await client.get_pvpc_prices(date(2026, 6, 12))

    assert series.last_update is None
    assert len(series.prices) == 1
