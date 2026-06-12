from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.stats import HeatmapCell, MonthlyEnergy, StatsOverview
from app.services.stats import arrivals_heatmap, energy_monthly, overview

router = APIRouter(prefix="/stats", tags=["stats"])

SiteParam = Annotated[
    str | None, Query(description="Restrict to one ACN site (caltech, jpl, office001).")
]


@router.get("/overview", response_model=StatsOverview)
async def read_overview(db: Annotated[AsyncSession, Depends(get_db)]) -> StatsOverview:
    return StatsOverview.model_validate(await overview(db))


@router.get("/energy-monthly", response_model=list[MonthlyEnergy])
async def read_energy_monthly(
    db: Annotated[AsyncSession, Depends(get_db)],
    site: SiteParam = None,
) -> list[MonthlyEnergy]:
    rows = await energy_monthly(db, site=site)
    return [MonthlyEnergy.model_validate(row) for row in rows]


@router.get("/arrivals-heatmap", response_model=list[HeatmapCell])
async def read_arrivals_heatmap(
    db: Annotated[AsyncSession, Depends(get_db)],
    site: SiteParam = None,
) -> list[HeatmapCell]:
    rows = await arrivals_heatmap(db, site=site)
    return [HeatmapCell.model_validate(row) for row in rows]
