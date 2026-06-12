import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.charging_point import ChargingPoint, Connector, Evse
from app.models.tariff import Tariff

Bbox = tuple[Decimal, Decimal, Decimal, Decimal]
"""(min_lng, min_lat, max_lng, max_lat) — GeoJSON bbox axis order."""


def _base_query() -> Select[tuple[ChargingPoint]]:
    return (
        select(ChargingPoint)
        .where(ChargingPoint.archived_at.is_(None))
        .options(
            selectinload(ChargingPoint.evses)
            .selectinload(Evse.connectors)
            .selectinload(Connector.tariff)
        )
    )


async def list_points(
    db: AsyncSession,
    *,
    bbox: Bbox | None = None,
    connector_standard: str | None = None,
    max_price_per_kwh: Decimal | None = None,
) -> Sequence[ChargingPoint]:
    stmt = _base_query().order_by(ChargingPoint.id)
    if bbox is not None:
        min_lng, min_lat, max_lng, max_lat = bbox
        stmt = stmt.where(
            ChargingPoint.longitude.between(min_lng, max_lng),
            ChargingPoint.latitude.between(min_lat, max_lat),
        )
    if connector_standard is not None:
        stmt = stmt.where(
            ChargingPoint.evses.any(Evse.connectors.any(Connector.standard == connector_standard))
        )
    if max_price_per_kwh is not None:
        stmt = stmt.where(
            ChargingPoint.evses.any(
                Evse.connectors.any(Connector.tariff.has(Tariff.price_per_kwh <= max_price_per_kwh))
            )
        )
    return (await db.execute(stmt)).scalars().all()


async def get_point(db: AsyncSession, point_id: uuid.UUID) -> ChargingPoint | None:
    stmt = _base_query().where(ChargingPoint.id == point_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def map_feature_collection(db: AsyncSession) -> dict[str, Any]:
    """Slim GeoJSON FeatureCollection for the map: one aggregated row per point.

    Duplicate evse rows from the connector join don't skew bool_and/bool_or
    (AND/OR are idempotent), and aggregates skip NULLs, so bool_or IS NULL
    means no evse reported an operational status.
    """
    aggregate_status = case(
        (func.bool_or(Evse.is_operational).is_(None), "unknown"),
        (func.bool_and(Evse.is_operational), "operational"),
        (func.bool_or(Evse.is_operational), "partial"),
        else_="inoperative",
    )
    stmt = (
        select(
            ChargingPoint.id,
            ChargingPoint.name,
            ChargingPoint.cpo_name,
            ChargingPoint.latitude,
            ChargingPoint.longitude,
            aggregate_status.label("aggregate_status"),
            func.array_agg(distinct(Connector.standard))
            .filter(Connector.standard.is_not(None))
            .label("standards"),
            func.max(Connector.max_electric_power).label("max_power_w"),
            func.min(Tariff.price_per_kwh).label("min_price_per_kwh"),
        )
        .outerjoin(Evse, Evse.charging_point_id == ChargingPoint.id)
        .outerjoin(Connector, Connector.evse_id == Evse.id)
        .outerjoin(Tariff, Tariff.id == Connector.tariff_id)
        .where(ChargingPoint.archived_at.is_(None))
        .group_by(ChargingPoint.id)
    )
    rows = (await db.execute(stmt)).all()

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row.longitude), float(row.latitude)],
            },
            "properties": {
                "id": str(row.id),
                "name": row.name,
                "cpo_name": row.cpo_name,
                "aggregate_status": row.aggregate_status,
                "standards": sorted(row.standards) if row.standards else [],
                "max_power_w": row.max_power_w,
                "min_price_per_kwh": (
                    float(row.min_price_per_kwh) if row.min_price_per_kwh is not None else None
                ),
            },
        }
        for row in rows
    ]
    return {"type": "FeatureCollection", "features": features}
