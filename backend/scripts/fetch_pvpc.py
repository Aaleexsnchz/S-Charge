"""Daily PVPC fetch with gap-backfill.

apidatos.ree.es publishes the hourly PVPC series with a lag (today fills in
during the day; the next day late in the evening, often answering 500 until
then). Each run re-fetches every day from the last stored hour through tomorrow,
so a multi-day hole (e.g. the host being asleep) self-heals on the next tick.
"""

import asyncio
import sys
from datetime import UTC, date, datetime, timedelta

from app.database import SessionLocal
from app.etl.pvpc import import_pvpc_prices
from app.integrations.ree import ReeClient
from app.models.price import ElectricityPrice
from app.services.pvpc import MARKET_TZ
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

MAX_BACKFILL_DAYS = 60


async def _start_day(db: AsyncSession, today: date) -> date:
    latest = await db.scalar(select(func.max(ElectricityPrice.hour_start)))
    if latest is None:
        return today - timedelta(days=1)
    last_day = latest.astimezone(MARKET_TZ).date()
    return max(last_day, today - timedelta(days=MAX_BACKFILL_DAYS))


async def main() -> int:
    today = datetime.now(UTC).astimezone(MARKET_TZ).date()
    end = today + timedelta(days=1)
    async with SessionLocal() as db, ReeClient() as client:
        day = await _start_day(db, today)
        while day <= end:
            rows = await import_pvpc_prices(client, db, day)
            await db.commit()
            print(f"  {day.isoformat()}: {rows} hourly prices")
            day += timedelta(days=1)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
