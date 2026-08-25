from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.models.price import ElectricityPrice
from app.services.pvpc import price_for_hour
from sqlalchemy.ext.asyncio import AsyncSession

MADRID = ZoneInfo("Europe/Madrid")


async def test_price_for_hour_floors_to_slot(db_session: AsyncSession) -> None:
    slot = datetime(2026, 6, 26, 9, 0, tzinfo=MADRID)
    db_session.add(ElectricityPrice(hour_start=slot, price_per_kwh=Decimal("0.09500")))
    await db_session.flush()

    price = await price_for_hour(db_session, slot.replace(minute=59, second=59))

    assert price == Decimal("0.09500")
