import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Select, select
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
