from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleRead

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleRead])
async def read_vehicles(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[VehicleRead]:
    stmt = select(Vehicle).order_by(Vehicle.make, Vehicle.model)
    vehicles = (await db.execute(stmt)).scalars().all()
    return [VehicleRead.model_validate(vehicle) for vehicle in vehicles]
