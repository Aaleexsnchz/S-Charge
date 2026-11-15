"""Reads of the regulated wholesale price (PVPC) this mirror has ingested.

What electricity costs the country, not what a charging operator charges for it
-- that is a tariff, and it lives in :mod:`app.services.tariff_pricing`.
"""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price import ElectricityPrice

MARKET_TZ = ZoneInfo("Europe/Madrid")
"""REE publishes PVPC against the peninsular clock, so every slot is local to it."""


async def prices_for_day(db: AsyncSession, day: date) -> Sequence[ElectricityPrice]:
    """Hourly PVPC rows for a Madrid-local calendar day, ordered by hour."""
    day_start = datetime.combine(day, time.min, tzinfo=MARKET_TZ)
    day_end = day_start + timedelta(days=1)
    stmt = (
        select(ElectricityPrice)
        .where(ElectricityPrice.hour_start >= day_start)
        .where(ElectricityPrice.hour_start < day_end)
        .order_by(ElectricityPrice.hour_start)
    )
    return (await db.execute(stmt)).scalars().all()
