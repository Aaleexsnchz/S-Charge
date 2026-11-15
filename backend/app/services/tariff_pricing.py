import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import CursorResult, text
from sqlalchemy.ext.asyncio import AsyncSession

MAX_PLAUSIBLE_PRICE_EUR_PER_KWH = Decimal("2")

_APPLICABLE_JOINS = """
    FROM connectors c
    JOIN evses ev ON ev.id = c.evse_id
    JOIN charging_points p ON p.id = ev.charging_point_id
    JOIN tariffs tf ON tf.id = c.tariff_id
    JOIN tariff_elements e ON e.tariff_id = c.tariff_id
"""

# One instant, for the two statements that answer "what does it cost now".
_LOCAL_TS_AT = """
    CROSS JOIN LATERAL (
        SELECT CAST(:at AS timestamptz) AS ts
    ) g
"""

# Every minute of a charging window, for the one that prices a session spanning
# bands. A row per minute rather than an interval intersection: the bands the
# window crosses are few, but a session's power is not constant across them, so
# the caller has to weight each minute by the energy actually delivered in it.
_LOCAL_TS_SERIES = """
    CROSS JOIN LATERAL (
        SELECT generate_series(CAST(:at AS timestamptz),
                               CAST(:until AS timestamptz),
                               interval '1 minute') AS ts
    ) g
"""

_BAND_BOUNDS = """
    CROSS JOIN LATERAL (
        SELECT date_trunc('minute', g.ts AT TIME ZONE p.time_zone) AS local_ts
    ) l
    -- The end minute is inclusive: REVE publishes bands as 00:00-06:59 /
    -- 07:00-22:59, so reading end_time as exclusive leaves a one-minute hole at
    -- every boundary. OCPI's "end_time 00:00 means end of day" is what the
    -- NULLIF normalises, which also makes a 23:00-00:00 band read as 23:00-23:59.
    CROSS JOIN LATERAL (
        SELECT COALESCE(e.start_time, '00:00'::time) AS lo,
               COALESCE(NULLIF(e.end_time, '00:00'::time), '23:59'::time) AS hi
    ) band
"""

_APPLICABLE_SOURCE = _APPLICABLE_JOINS + _LOCAL_TS_AT + _BAND_BOUNDS

# Everything that gates a band except the time-of-day window, which the resolver
# applies to find the band for one instant and the schedule returns instead.
_APPLICABLE_RESTRICTIONS = """
    -- A tariff past its own validity window does not price anything. These are
    -- ended promotions, not stale defaults: they average a third of the price of
    -- the live ones, so serving them sends a driver to a charger expecting to
    -- pay 0.11 where they will be billed 0.35.
    WHERE (tf.valid_from IS NULL OR tf.valid_from <= :at)
      AND (tf.valid_to IS NULL OR tf.valid_to >= :at)
      AND e.reservation IS NULL
      AND e.min_kwh IS NULL
      AND e.min_current IS NULL
      AND e.min_duration_s IS NULL
      AND (e.start_date IS NULL OR l.local_ts::date >= e.start_date)
      -- OCPI calls end_date exclusive, but 275 of the 406 dated bands here set
      -- start_date = end_date for a single day, which exclusive reading would
      -- make unmatchable on any date at all. Same inclusive-end habit as the
      -- end_time bands.
      AND (e.end_date IS NULL OR l.local_ts::date <= e.end_date)
      AND (
            e.days_of_week IS NULL
            OR (ARRAY['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY',
                      'SATURDAY','SUNDAY'])[EXTRACT(isodow FROM l.local_ts)::int]
                 = ANY(e.days_of_week)
          )
      -- OCPI gates these on live session power; the connector's rating stands
      -- in for it here, and a session never reaches the rating exactly, so the
      -- bound is inclusive: a 22 kW connector belongs in the "up to 22 kW" band.
      AND (e.min_power_kw IS NULL OR c.max_electric_power IS NULL
           OR c.max_electric_power >= e.min_power_kw * 1000)
      AND (e.max_power_kw IS NULL OR c.max_electric_power IS NULL
           OR c.max_electric_power <= e.max_power_kw * 1000)
"""

_IN_BAND_AT = """
      AND CASE
              WHEN band.lo <= band.hi
                  THEN l.local_ts::time BETWEEN band.lo AND band.hi
              ELSE l.local_ts::time >= band.lo OR l.local_ts::time <= band.hi
          END
"""

_RESTRICTION_COLUMNS = """
           -- Any restriction at all, not how many: counting them lets a band
           -- with a time window outrank a tighter power band, which inverts
           -- the "up to 22 kW" rule below. This only has to separate a real
           -- band from the tariff's unrestricted fallback.
           (e.start_time IS NOT NULL OR e.end_time IS NOT NULL
            OR e.start_date IS NOT NULL OR e.end_date IS NOT NULL
            OR e.days_of_week IS NOT NULL
            OR e.min_power_kw IS NOT NULL OR e.max_power_kw IS NOT NULL
            OR e.max_kwh IS NOT NULL OR e.max_current IS NOT NULL
            OR e.max_duration_s IS NOT NULL) AS is_restricted
"""

# S608 on both statements below reads the interpolated fragments as an injection
# vector. They are module constants; every value is a bound parameter.
_RECOMPUTE_SQL = text(f"""
WITH applicable AS (
    SELECT c.id AS connector_id, e.component_type, e.price,
           e.max_power_kw, e.element_index,
{_RESTRICTION_COLUMNS}
{_APPLICABLE_SOURCE}
{_APPLICABLE_RESTRICTIONS}
{_IN_BAND_AT}
),
free_agg AS (
    -- Free means the source said so: every applicable component is zero AND one
    -- of them prices energy. A lone `FLAT 0` with no vat, step_size 0 and no
    -- ENERGY band is an unfilled template, not a free charger -- the CPOs that
    -- publish them price the rest of their estate normally.
    -- bool_and ignores NULLs, so a component with no price at all would pass
    -- as zero and publish an unfilled record as free.
    SELECT connector_id,
           bool_and(price IS NOT NULL AND price = 0)
             AND bool_or(component_type = 'ENERGY') AS all_free
    FROM applicable GROUP BY connector_id
),
chosen AS (
    -- An unrestricted band is the tariff's fallback, so the more specific band
    -- wins over it: 127 tariffs publish both, and ordering by element_index
    -- alone hands 1,247 connectors the fallback price inside a cheaper window.
    SELECT DISTINCT ON (connector_id) connector_id, component_type, price
    FROM applicable
    -- A zero-priced TIME or FLAT band establishes no pricing model; it is the
    -- unfilled-template shape above. Only an explicit ENERGY 0 means free.
    WHERE component_type = 'ENERGY' OR price <> 0
    ORDER BY connector_id,
             CASE component_type
                 WHEN 'ENERGY' THEN 0
                 WHEN 'TIME' THEN 1
                 WHEN 'PARKING_TIME' THEN 2
                 WHEN 'FLAT' THEN 3
                 ELSE 4
             END,
             is_restricted DESC,
             max_power_kw ASC NULLS LAST,
             element_index
),
resolved AS (
    SELECT c.id,
           CASE
               WHEN f.all_free THEN 'free'
               WHEN ch.component_type = 'ENERGY'
                    AND ch.price BETWEEN 0 AND :max_price THEN 'energy'
               WHEN ch.component_type IN ('TIME', 'PARKING_TIME') THEN 'time'
               WHEN ch.component_type = 'FLAT' THEN 'flat'
               ELSE 'unknown'
           END AS kind,
           CASE
               WHEN NOT COALESCE(f.all_free, false)
                    AND ch.component_type = 'ENERGY'
                    AND ch.price BETWEEN 0 AND :max_price THEN ch.price
           END AS price
    FROM connectors c
    LEFT JOIN chosen ch ON ch.connector_id = c.id
    LEFT JOIN free_agg f ON f.connector_id = c.id
)
UPDATE connectors c
SET pricing_kind = r.kind::connector_pricing_kind,
    current_price_per_kwh = r.price
FROM resolved r
WHERE c.id = r.id
  AND (c.pricing_kind IS DISTINCT FROM r.kind::connector_pricing_kind
       OR c.current_price_per_kwh IS DISTINCT FROM r.price)
""")  # noqa: S608


async def recompute_connector_prices(
    db: AsyncSession, at: datetime | None = None
) -> int:
    """Resolve every connector's price band for ``at`` and store the result.

    The price a driver pays varies by time of day *and* by connector power, so
    it is unique only at the connector — a tariff shared across connectors of
    different power cannot carry one correct price. This denormalises the band
    that applies now onto ``connectors``; the bands themselves stay queryable in
    ``tariff_elements`` for anything that needs a different instant.

    Restrictions are read against the charging point's own local time. The ones
    that only a live session can answer (energy drawn, current, elapsed time)
    are treated as *not yet active*: a band gated behind ``min_kwh`` does not
    price the first kWh. Bands capped by a ``max_*`` do apply from the start.

    Returns the number of connectors whose stored price actually changed.
    """
    result = await db.execute(
        _RECOMPUTE_SQL,
        {
            "at": at or datetime.now(UTC),
            "max_price": MAX_PLAUSIBLE_PRICE_EUR_PER_KWH,
        },
    )
    return cast(CursorResult[Any], result).rowcount


_SCHEDULE_SQL = text(f"""
WITH applicable AS (
    SELECT c.id AS connector_id, e.price, e.element_index, e.max_power_kw,
           band.lo AS start_time, band.hi AS end_time,
           l.local_ts::time AS local_time,
           (e.start_time IS NOT NULL OR e.end_time IS NOT NULL) AS has_window,
{_RESTRICTION_COLUMNS}
{_APPLICABLE_SOURCE}
{_APPLICABLE_RESTRICTIONS}
      AND ev.charging_point_id = :point_id
      AND e.component_type = 'ENERGY'
      AND e.price BETWEEN 0 AND :max_price
),
-- A tariff's unrestricted band is the fallback the resolver drops back to, not
-- an entry in the schedule: listing it beside the real windows shows an all-day
-- price that never applies, at 127 tariffs that publish both.
windowed AS (
    SELECT a.* FROM applicable a
    WHERE a.has_window
       OR NOT EXISTS (
           SELECT 1 FROM applicable o
           WHERE o.connector_id = a.connector_id AND o.has_window
       )
),
ranked AS (
    SELECT DISTINCT ON (connector_id, start_time, end_time)
           connector_id, start_time, end_time, price, local_time,
           is_restricted, max_power_kw, element_index
    FROM windowed
    ORDER BY connector_id, start_time, end_time, is_restricted DESC,
             max_power_kw ASC NULLS LAST, element_index
),
-- REVE writes both bounds inclusive, so 00:00-18:00 and 18:00-22:00 both contain
-- 18:00. Exactly one row may be current or the page highlights two prices, so
-- the tie breaks the way the resolver breaks it.
current_band AS (
    SELECT DISTINCT ON (connector_id) connector_id, start_time, end_time
    FROM ranked
    WHERE CASE
              WHEN start_time <= end_time
                  THEN local_time BETWEEN start_time AND end_time
              ELSE local_time >= start_time OR local_time <= end_time
          END
    ORDER BY connector_id, is_restricted DESC, max_power_kw ASC NULLS LAST,
             element_index
)
SELECT r.connector_id, r.start_time, r.end_time, r.price,
       (cb.connector_id IS NOT NULL) AS is_current
FROM ranked r
LEFT JOIN current_band cb
       ON cb.connector_id = r.connector_id
      AND cb.start_time = r.start_time
      AND cb.end_time = r.end_time
ORDER BY r.connector_id, r.start_time
""")  # noqa: S608


@dataclass(frozen=True)
class PriceBand:
    start_time: time
    end_time: time
    price_per_kwh: Decimal
    is_current: bool


async def connector_price_bands(
    db: AsyncSession, point_id: uuid.UUID, at: datetime | None = None
) -> dict[uuid.UUID, list[PriceBand]]:
    """The energy bands each of a point's connectors is priced by today.

    Only connectors whose price actually varies across the day are returned: a
    single band is the price, not a schedule, and 96% of priced connectors have
    exactly one. Bands are gated to the connector's own power rating, so what
    comes back is what *this* connector charges rather than what its tariff
    publishes for the whole station.
    """
    rows = (
        await db.execute(
            _SCHEDULE_SQL,
            {
                "point_id": point_id,
                "at": at or datetime.now(UTC),
                "max_price": MAX_PLAUSIBLE_PRICE_EUR_PER_KWH,
            },
        )
    ).all()

    bands: dict[uuid.UUID, list[PriceBand]] = defaultdict(list)
    for row in rows:
        bands[row.connector_id].append(
            PriceBand(
                start_time=row.start_time,
                end_time=row.end_time,
                price_per_kwh=row.price,
                is_current=row.is_current,
            )
        )
    return {
        connector_id: connector_bands
        for connector_id, connector_bands in bands.items()
        if len(connector_bands) > 1
    }


@dataclass(frozen=True)
class ConnectorSchedule:
    connector_ids: list[uuid.UUID]
    bands: list[PriceBand]


async def point_price_schedules(
    db: AsyncSession, point_id: uuid.UUID, at: datetime | None = None
) -> list[ConnectorSchedule]:
    """A point's price schedules, one per distinct set of bands.

    Connectors are grouped because 92% of the points that price by time of day
    charge every connector the same way, and repeating one identical table per
    connector is noise. The 8% that differ keep a table each: the connector is
    the grain where the price is unique, so a point-level schedule would be a
    claim the data does not support.
    """
    by_connector = await connector_price_bands(db, point_id, at)
    grouped: dict[tuple[PriceBand, ...], list[uuid.UUID]] = defaultdict(list)
    for connector_id, bands in by_connector.items():
        grouped[tuple(bands)].append(connector_id)
    return [
        ConnectorSchedule(connector_ids=sorted(ids, key=str), bands=list(bands))
        for bands, ids in grouped.items()
    ]


_WINDOW_SQL = text(f"""
WITH applicable AS (
    SELECT g.ts, e.price,
           e.element_index, e.max_power_kw,
{_RESTRICTION_COLUMNS}
{_APPLICABLE_JOINS}
{_LOCAL_TS_SERIES}
{_BAND_BOUNDS}
{_APPLICABLE_RESTRICTIONS}
{_IN_BAND_AT}
      AND c.id = :connector_id
      AND e.component_type = 'ENERGY'
      AND e.price BETWEEN 0 AND :max_price
)
SELECT DISTINCT ON (ts) ts, price
FROM applicable
ORDER BY ts, is_restricted DESC, max_power_kw ASC NULLS LAST, element_index
""")  # noqa: S608


async def connector_prices_over(
    db: AsyncSession, connector_id: uuid.UUID, start: datetime, end: datetime
) -> dict[datetime, Decimal]:
    """The per-minute energy price a connector charges between ``start`` and ``end``.

    A minute with no applicable band is absent rather than zero: a session that
    runs into an hour the tariff does not price has no cost for it, and inventing
    one would be the same claim as pricing an unpriced connector.
    """
    rows = (
        await db.execute(
            _WINDOW_SQL,
            {
                "connector_id": connector_id,
                "at": start,
                "until": end,
                "max_price": MAX_PLAUSIBLE_PRICE_EUR_PER_KWH,
            },
        )
    ).all()
    return {row.ts: row.price for row in rows}
