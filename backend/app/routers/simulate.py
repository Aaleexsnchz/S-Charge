from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.simulation import SimulationRequest, SimulationResult
from app.services.simulation import (
    ConnectorNotFound,
    DCNotSupported,
    InvalidConnectorPower,
    VehicleNotFound,
    run_simulation,
)

router = APIRouter(prefix="/simulate", tags=["simulate"])


@router.post("", response_model=SimulationResult)
async def simulate(
    request: SimulationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SimulationResult:
    try:
        return await run_simulation(db, request)
    except VehicleNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="vehicle not found"
        ) from None
    except ConnectorNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="connector not found"
        ) from None
    except DCNotSupported:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="vehicle does not support DC charging",
        ) from None
    except InvalidConnectorPower:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="connector has no usable power rating",
        ) from None
