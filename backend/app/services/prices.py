from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price import ElectricityPrice

MADRID = ZoneInfo("Europe/Madrid")


async def prices_for_day(db: AsyncSession, day: date) -> Sequence[ElectricityPrice]:
    """Hourly PVPC rows for a Madrid-local calendar day, ordered by hour."""
    day_start = datetime.combine(day, time.min, tzinfo=MADRID)
    day_end = day_start + timedelta(days=1)
    stmt = (
        select(ElectricityPrice)
        .where(ElectricityPrice.hour_start >= day_start)
        .where(ElectricityPrice.hour_start < day_end)
        .order_by(ElectricityPrice.hour_start)
    )
    return (await db.execute(stmt)).scalars().all()
