from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.vehicle import VehicleRead
from app.services.vehicles import list_vehicles

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleRead])
async def read_vehicles(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[VehicleRead]:
    vehicles = await list_vehicles(db)
    return [VehicleRead.model_validate(vehicle) for vehicle in vehicles]
