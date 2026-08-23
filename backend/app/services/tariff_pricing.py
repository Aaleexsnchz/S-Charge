from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import CursorResult, text
from sqlalchemy.ext.asyncio import AsyncSession

MAX_PLAUSIBLE_PRICE_EUR_PER_KWH = Decimal("2")

_RECOMPUTE_SQL = text("""
WITH applicable AS (
    SELECT c.id AS connector_id, e.component_type, e.price,
           e.max_power_kw, e.element_index,
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
    FROM connectors c
    JOIN evses ev ON ev.id = c.evse_id
    JOIN charging_points p ON p.id = ev.charging_point_id
    JOIN tariffs tf ON tf.id = c.tariff_id
    JOIN tariff_elements e ON e.tariff_id = c.tariff_id
    CROSS JOIN LATERAL (
        SELECT date_trunc('minute', :at AT TIME ZONE p.time_zone) AS local_ts
    ) l
    -- Likewise the end minute: REVE publishes bands as 00:00-06:59 / 07:00-22:59,
    -- so reading end_time as exclusive leaves a one-minute hole at every
    -- boundary. OCPI's "end_time 00:00 means end of day" is what the NULLIF
    -- normalises, which also makes a 23:00-00:00 band read as 23:00-23:59.
    CROSS JOIN LATERAL (
        SELECT COALESCE(e.start_time, '00:00'::time) AS lo,
               COALESCE(NULLIF(e.end_time, '00:00'::time), '23:59'::time) AS hi
    ) band
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
      -- end_time bands below.
      AND (e.end_date IS NULL OR l.local_ts::date <= e.end_date)
      AND CASE
              WHEN band.lo <= band.hi
                  THEN l.local_ts::time BETWEEN band.lo AND band.hi
              ELSE l.local_ts::time >= band.lo OR l.local_ts::time <= band.hi
          END
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
""")


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
