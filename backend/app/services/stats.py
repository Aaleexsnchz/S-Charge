from typing import Any

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acn import AcnSession

_LOCAL_TIME = func.timezone(func.coalesce(AcnSession.time_zone, "UTC"), AcnSession.connection_time)

_DURATION_MIN = func.extract("epoch", AcnSession.disconnect_time - AcnSession.connection_time) / 60


def _site_rollup() -> Any:
    return (
        func.count().label("sessions"),
        func.coalesce(func.sum(AcnSession.kwh_delivered), 0).label("total_kwh"),
        func.avg(AcnSession.kwh_delivered).label("avg_kwh"),
        func.avg(_DURATION_MIN).label("avg_duration_min"),
    )


def _rounded(value: Any, digits: int = 2) -> float | None:
    return round(float(value), digits) if value is not None else None


async def overview(db: AsyncSession) -> dict[str, Any]:
    totals = (await db.execute(select(*_site_rollup()))).one()
    per_site = (
        await db.execute(
            select(AcnSession.site, *_site_rollup())
            .group_by(AcnSession.site)
            .order_by(AcnSession.site)
        )
    ).all()

    def _shape(row: Any) -> dict[str, Any]:
        return {
            "sessions": row.sessions,
            "total_kwh": _rounded(row.total_kwh) or 0.0,
            "avg_kwh": _rounded(row.avg_kwh),
            "avg_duration_min": _rounded(row.avg_duration_min, 1),
        }

    return {
        **_shape(totals),
        "sites": [{"site": row.site, **_shape(row)} for row in per_site],
    }


async def energy_monthly(db: AsyncSession, site: str | None = None) -> list[dict[str, Any]]:
    month = func.to_char(func.date_trunc("month", _LOCAL_TIME), "YYYY-MM").label("month")
    stmt = (
        select(
            month,
            func.count().label("sessions"),
            func.coalesce(func.sum(AcnSession.kwh_delivered), 0).label("kwh"),
        )
        .group_by(month)
        .order_by(month)
    )
    if site is not None:
        stmt = stmt.where(AcnSession.site == site)
    rows = (await db.execute(stmt)).all()
    return [
        {"month": row.month, "sessions": row.sessions, "kwh": _rounded(row.kwh) or 0.0}
        for row in rows
    ]


async def arrivals_heatmap(db: AsyncSession, site: str | None = None) -> list[dict[str, Any]]:
    """Session arrivals bucketed by site-local weekday (0=Monday) and hour."""
    weekday = cast(func.extract("isodow", _LOCAL_TIME) - 1, Integer).label("weekday")
    hour = cast(func.extract("hour", _LOCAL_TIME), Integer).label("hour")
    stmt = (
        select(weekday, hour, func.count().label("sessions"))
        .group_by(weekday, hour)
        .order_by(weekday, hour)
    )
    if site is not None:
        stmt = stmt.where(AcnSession.site == site)
    rows = (await db.execute(stmt)).all()
    return [{"weekday": row.weekday, "hour": row.hour, "sessions": row.sessions} for row in rows]
