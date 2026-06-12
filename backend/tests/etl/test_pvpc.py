from datetime import date
from decimal import Decimal

from pytest_httpx import HTTPXMock
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.pvpc import import_pvpc_prices
from app.integrations.ree import ReeClient
from app.models.price import ElectricityPrice

BASE_URL = "https://ree.test"
DAY_URL = (
    f"{BASE_URL}/es/datos/mercados/precios-mercados-tiempo-real"
    "?start_date=2026-06-12T00%3A00&end_date=2026-06-12T23%3A59&time_trunc=hour"
)


def _payload(price_mwh: float) -> dict:
    return {
        "included": [
            {
                "id": "1001",
                "attributes": {
                    "title": "PVPC",
                    "values": [{"value": price_mwh, "datetime": "2026-06-12T00:00:00.000+02:00"}],
                },
            }
        ]
    }


async def test_import_upserts_and_is_idempotent(
    db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=DAY_URL, json=_payload(85.21))
    httpx_mock.add_response(url=DAY_URL, json=_payload(99.99))

    async with ReeClient(base_url=BASE_URL) as client:
        assert await import_pvpc_prices(client, db_session, date(2026, 6, 12)) == 1
        assert await import_pvpc_prices(client, db_session, date(2026, 6, 12)) == 1

    count = (
        await db_session.execute(select(func.count()).select_from(ElectricityPrice))
    ).scalar_one()
    assert count == 1
    row = (await db_session.execute(select(ElectricityPrice))).scalar_one()
    assert row.price_per_kwh == Decimal("0.09999")
