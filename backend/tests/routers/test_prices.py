from datetime import UTC, datetime
from decimal import Decimal

from app.models.price import ElectricityPrice
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _price(hour_start: datetime, value: str) -> ElectricityPrice:
    return ElectricityPrice(hour_start=hour_start, price_per_kwh=Decimal(value))


async def test_prices_for_madrid_local_day(
    auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    db_session.add_all(
        [
            # 22:00 UTC on the 11th is 00:00 on the 12th in Madrid (CEST)
            _price(datetime(2026, 6, 11, 22, 0, tzinfo=UTC), "0.08521"),
            _price(datetime(2026, 6, 12, 12, 0, tzinfo=UTC), "0.12000"),
            # 22:00 UTC on the 12th belongs to the 13th in Madrid
            _price(datetime(2026, 6, 12, 22, 0, tzinfo=UTC), "0.27220"),
        ]
    )
    await db_session.commit()

    response = await auth_client.get("/api/prices/today", params={"day": "2026-06-12"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["price_per_kwh"] == 0.08521
    assert body[1]["price_per_kwh"] == 0.12


async def test_prices_empty_day(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/prices/today", params={"day": "2030-01-01"})

    assert response.status_code == 200
    assert response.json() == []
