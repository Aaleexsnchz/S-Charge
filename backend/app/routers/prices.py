from datetime import UTC, date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.price import PricePoint
from app.services.prices import prices_for_day

router = APIRouter(prefix="/prices", tags=["prices"])

MADRID = ZoneInfo("Europe/Madrid")


@router.get("/today", response_model=list[PricePoint])
async def read_prices_today(
    db: Annotated[AsyncSession, Depends(get_db)],
    day: Annotated[
        date | None,
        Query(description="Madrid-local day, ISO format; defaults to today."),
    ] = None,
) -> list[PricePoint]:
    target = day if day is not None else datetime.now(UTC).astimezone(MADRID).date()
    rows = await prices_for_day(db, target)
    return [PricePoint.model_validate(row) for row in rows]
