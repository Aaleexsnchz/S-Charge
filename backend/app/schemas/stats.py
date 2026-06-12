from pydantic import BaseModel


class SiteStats(BaseModel):
    site: str
    sessions: int
    total_kwh: float
    avg_kwh: float | None
    avg_duration_min: float | None


class StatsOverview(BaseModel):
    sessions: int
    total_kwh: float
    avg_kwh: float | None
    avg_duration_min: float | None
    sites: list[SiteStats]


class MonthlyEnergy(BaseModel):
    month: str
    sessions: int
    kwh: float


class HeatmapCell(BaseModel):
    weekday: int
    """0 = Monday … 6 = Sunday, in site-local time."""
    hour: int
    sessions: int
