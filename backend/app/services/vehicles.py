from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import Vehicle


async def list_vehicles(db: AsyncSession) -> Sequence[Vehicle]:
    stmt = select(Vehicle).order_by(Vehicle.make, Vehicle.model)
    return (await db.execute(stmt)).scalars().all()
