"""Daily PVPC fetch: yesterday + today + tomorrow.

apidatos.ree.es publishes the hourly PVPC series with a lag (the current day
fills in during the day; the next day late in the evening, often answering 500
until then). Fetching a three-day window per tick backfills any gap the
previous tick left.
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.database import SessionLocal
from app.etl.pvpc import import_pvpc_prices
from app.integrations.ree import ReeClient

MADRID = ZoneInfo("Europe/Madrid")


async def main() -> int:
    today = datetime.now(UTC).astimezone(MADRID).date()
    async with SessionLocal() as db, ReeClient() as client:
        for day in (today - timedelta(days=1), today, today + timedelta(days=1)):
            rows = await import_pvpc_prices(client, db, day)
            await db.commit()
            print(f"  {day.isoformat()}: {rows} hourly prices")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
