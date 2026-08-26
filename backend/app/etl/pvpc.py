import uuid
from datetime import date

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.ree import ReeClient
from app.models.price import ElectricityPrice
from app.utils.audit import audit


async def import_pvpc_prices(client: ReeClient, db: AsyncSession, day: date) -> int:
    """Upsert the hourly PVPC curve for ``day``. The caller owns the transaction."""
    series = await client.get_pvpc_prices(day)
    for hour_start, price_per_kwh in series.prices:
        stmt = insert(ElectricityPrice).values(
            id=uuid.uuid4(),
            hour_start=hour_start,
            price_per_kwh=price_per_kwh,
            source_last_updated_at=series.last_update,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["hour_start"],
            set_={
                "price_per_kwh": stmt.excluded["price_per_kwh"],
                "source_last_updated_at": stmt.excluded["source_last_updated_at"],
            },
        )
        await db.execute(stmt)
    audit(
        "pvpc_etl_prices",
        day=day.isoformat(),
        rows=len(series.prices),
        source_last_updated_at=(
            series.last_update.isoformat() if series.last_update else None
        ),
    )
    return len(series.prices)
