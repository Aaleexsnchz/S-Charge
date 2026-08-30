import asyncio
import hashlib
import json
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypeGuard

from sqlalchemy import Select, case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.charging_point import ChargingPoint, Connector, Evse, PricingKind

Bbox = tuple[Decimal, Decimal, Decimal, Decimal]
"""(min_lng, min_lat, max_lng, max_lat) — GeoJSON bbox axis order."""

MAP_CACHE_TTL_SECONDS = 600
"""Bounded staleness for the map payload.

The catalogue moves at the REVE refresh's hourly cadence and prices at the
recompute tick's, so ten minutes is well inside one cycle. It is the map's
"from" price that ages here, never the authoritative one: the point detail
reads live.
"""


@dataclass(frozen=True)
class _CachedMap:
    body: bytes
    etag: str
    built_at: float


_map_cache: _CachedMap | None = None
_map_cache_lock = asyncio.Lock()


def reset_map_cache() -> None:
    """Drop the memoised payload. For tests, which change the catalogue between
    requests and would otherwise be served the previous test's answer."""
    global _map_cache
    _map_cache = None


def _is_fresh(cached: _CachedMap | None) -> TypeGuard[_CachedMap]:
    return (
        cached is not None
        and time.monotonic() - cached.built_at < MAP_CACHE_TTL_SECONDS
    )


async def cached_map_payload(db: AsyncSession) -> tuple[bytes, str]:
    """The serialised FeatureCollection and its ETag, built at most once per TTL.

    Two costs are being avoided, not one: the aggregate over every unarchived
    point, and serialising ~3.4 MB of JSON. Both used to run on every request
    for a payload identical to the one served a moment earlier.
    """
    global _map_cache
    cached = _map_cache
    if _is_fresh(cached):
        return cached.body, cached.etag

    async with _map_cache_lock:
        # Re-checked under the lock: without this, every request that arrived
        # while the first was building would rebuild it again on acquiring.
        cached = _map_cache
        if _is_fresh(cached):
            return cached.body, cached.etag

        collection = await map_feature_collection(db)
        body = json.dumps(collection, separators=(",", ":")).encode()
        etag = f'"{hashlib.sha256(body).hexdigest()[:32]}"'
        _map_cache = _CachedMap(body=body, etag=etag, built_at=time.monotonic())
        return body, etag

        collection = await map_feature_collection(db)
        body = json.dumps(collection, separators=(",", ":")).encode()
        etag = f'"{hashlib.sha256(body).hexdigest()[:32]}"'
        _map_cache = _CachedMap(body=body, etag=etag, built_at=time.monotonic())
        return body, etag


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
            ChargingPoint.evses.any(
                Evse.connectors.any(Connector.standard == connector_standard)
            )
        )
    if max_price_per_kwh is not None:
        # Free connectors carry no price, so a bare `<= max` would hide the
        # cheapest points on the map.
        stmt = stmt.where(
            ChargingPoint.evses.any(
                Evse.connectors.any(
                    or_(
                        Connector.pricing_kind == PricingKind.FREE,
                        Connector.current_price_per_kwh <= max_price_per_kwh,
                    )
                )
            )
        )
    return (await db.execute(stmt)).scalars().all()


async def get_point(db: AsyncSession, point_id: uuid.UUID) -> ChargingPoint | None:
    stmt = _base_query().where(ChargingPoint.id == point_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def map_feature_collection(db: AsyncSession) -> dict[str, Any]:
    """Slim GeoJSON FeatureCollection for the map: one aggregated row per point.

    Availability rollup over the EVSEs' (simulated) status. Duplicate evse rows
    from the connector join don't skew the aggregates, and ``count(status) == 0``
    means no evse has a status yet — i.e. unknown.
    """
    aggregate_status = case(
        (func.count(Evse.status) == 0, "unknown"),
        (func.bool_or(Evse.status == "AVAILABLE"), "available"),
        else_="occupied",
    )
    stmt = (
        select(
            ChargingPoint.id,
            ChargingPoint.latitude,
            ChargingPoint.longitude,
            aggregate_status.label("aggregate_status"),
            func.array_agg(distinct(Connector.standard))
            .filter(Connector.standard.is_not(None))
            .label("standards"),
            func.max(Connector.max_electric_power).label("max_power_w"),
            func.min(Connector.current_price_per_kwh).label("min_price_per_kwh"),
            func.bool_or(Connector.pricing_kind == PricingKind.FREE).label("has_free"),
        )
        .outerjoin(Evse, Evse.charging_point_id == ChargingPoint.id)
        .outerjoin(Connector, Connector.evse_id == Evse.id)
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
                "aggregate_status": row.aggregate_status,
                "standards": sorted(row.standards) if row.standards else [],
                "max_power_w": row.max_power_w,
                "min_price_per_kwh": (
                    float(row.min_price_per_kwh)
                    if row.min_price_per_kwh is not None
                    else None
                ),
                "has_free": bool(row.has_free),
            },
        }
        for row in rows
    ]
    return {"type": "FeatureCollection", "features": features}
