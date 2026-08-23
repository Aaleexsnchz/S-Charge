"""tariff bands and per-connector price

Revision ID: a1da13ad1e63
Revises: 84f452f47d53
Create Date: 2026-08-22 17:49:00.681289

The price REVE publishes varies by time of day *and* by connector power, so a
single ``price_per_kwh`` on the tariff was structurally incapable of being right
for the tariffs shared across connectors of different power. The bands move into
``tariff_elements`` and the resolved price onto the connector.

The backfill needs no network: every stored tariff already holds its complete
``elements`` array in ``raw_data``, because the flattening happened on the way
out, never on the way in.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1da13ad1e63"
down_revision: str | Sequence[str] | None = "84f452f47d53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

pricing_kind = postgresql.ENUM(
    "energy",
    "time",
    "flat",
    "free",
    "unknown",
    name="connector_pricing_kind",
    create_type=False,
)


BACKFILL_ELEMENTS = """
INSERT INTO tariff_elements (
    id, tariff_id, element_index, component_type, price, vat, step_size,
    start_time, end_time, start_date, end_date, days_of_week,
    min_kwh, max_kwh, min_current, max_current,
    min_power_kw, max_power_kw, min_duration_s, max_duration_s, reservation
)
-- A 0 in a restriction bound is REVE's "not set", not a real limit: a band
-- capped at max_power = 0 matches no connector, and min_duration = 0 gates
-- nothing. NULLIF folds them away; raw_data keeps the literal source.
SELECT
    gen_random_uuid(),
    t.id,
    (el.ord - 1)::int,
    comp ->> 'type',
    NULLIF(comp ->> 'price', '')::numeric,
    NULLIF(comp ->> 'vat', '')::numeric,
    NULLIF(comp ->> 'step_size', '')::numeric::int,
    NULLIF(el.value -> 'restrictions' ->> 'start_time', '')::time,
    NULLIF(el.value -> 'restrictions' ->> 'end_time', '')::time,
    NULLIF(el.value -> 'restrictions' ->> 'start_date', '')::date,
    NULLIF(el.value -> 'restrictions' ->> 'end_date', '')::date,
    (
        SELECT array_agg(upper(d))
        FROM jsonb_array_elements_text(el.value -> 'restrictions' -> 'day_of_week') d
    ),
    NULLIF(NULLIF(el.value -> 'restrictions' ->> 'min_kwh', '')::numeric, 0),
    NULLIF(NULLIF(el.value -> 'restrictions' ->> 'max_kwh', '')::numeric, 0),
    NULLIF(NULLIF(el.value -> 'restrictions' ->> 'min_current', '')::numeric, 0),
    NULLIF(NULLIF(el.value -> 'restrictions' ->> 'max_current', '')::numeric, 0),
    NULLIF(NULLIF(el.value -> 'restrictions' ->> 'min_power', '')::numeric, 0),
    NULLIF(NULLIF(el.value -> 'restrictions' ->> 'max_power', '')::numeric, 0),
    NULLIF(NULLIF(el.value -> 'restrictions' ->> 'min_duration', '')::numeric::int, 0),
    NULLIF(NULLIF(el.value -> 'restrictions' ->> 'max_duration', '')::numeric::int, 0),
    NULLIF(el.value -> 'restrictions' ->> 'reservation', '')::text
FROM tariffs t
CROSS JOIN LATERAL
    jsonb_array_elements(t.raw_data -> 'elements') WITH ORDINALITY AS el(value, ord)
CROSS JOIN LATERAL
    jsonb_array_elements(el.value -> 'price_components') AS comp
WHERE jsonb_typeof(t.raw_data -> 'elements') = 'array'
  AND jsonb_typeof(el.value -> 'price_components') = 'array'
  AND comp ->> 'type' IS NOT NULL
"""

# A frozen copy of app.services.tariff_pricing._RECOMPUTE_SQL. Importing it would
# break `alembic upgrade head` the day that function's shape changes, so the
# duplication is deliberate.
BACKFILL_CONNECTOR_PRICES = """
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
        SELECT date_trunc('minute', now() AT TIME ZONE p.time_zone) AS local_ts
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
    WHERE (tf.valid_from IS NULL OR tf.valid_from <= now())
      AND (tf.valid_to IS NULL OR tf.valid_to >= now())
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
                    AND ch.price BETWEEN 0 AND 2 THEN 'energy'
               WHEN ch.component_type IN ('TIME', 'PARKING_TIME') THEN 'time'
               WHEN ch.component_type = 'FLAT' THEN 'flat'
               ELSE 'unknown'
           END AS kind,
           CASE
               WHEN NOT COALESCE(f.all_free, false)
                    AND ch.component_type = 'ENERGY'
                    AND ch.price BETWEEN 0 AND 2 THEN ch.price
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
"""


def upgrade() -> None:
    pricing_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tariff_elements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tariff_id", sa.Uuid(), nullable=False),
        sa.Column("element_index", sa.Integer(), nullable=False),
        sa.Column("component_type", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("vat", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("step_size", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("days_of_week", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("min_kwh", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("max_kwh", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("min_current", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("max_current", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("min_power_kw", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("max_power_kw", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("min_duration_s", sa.Integer(), nullable=True),
        sa.Column("max_duration_s", sa.Integer(), nullable=True),
        sa.Column("reservation", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tariff_elements_tariff_id", "tariff_elements", ["tariff_id"], unique=False
    )
    op.add_column(
        "connectors",
        sa.Column(
            "pricing_kind", pricing_kind, server_default="unknown", nullable=False
        ),
    )
    op.add_column(
        "connectors",
        sa.Column("current_price_per_kwh", sa.Numeric(precision=8, scale=4)),
    )

    op.execute(BACKFILL_ELEMENTS)
    # The table was created and filled in this same transaction, so the planner
    # still sees it as empty; without stats it picks a nested loop over 46k
    # connectors and the deploy hangs.
    op.execute("ANALYZE tariff_elements")
    op.execute(BACKFILL_CONNECTOR_PRICES)

    op.drop_column("tariffs", "vat_percentage")
    op.drop_column("tariffs", "price_component_type")
    op.drop_column("tariffs", "step_size")
    op.drop_column("tariffs", "price_per_kwh")


def downgrade() -> None:
    op.add_column(
        "tariffs",
        sa.Column("price_per_kwh", sa.NUMERIC(precision=8, scale=4), nullable=True),
    )
    op.add_column("tariffs", sa.Column("step_size", sa.INTEGER(), nullable=True))
    op.add_column(
        "tariffs", sa.Column("price_component_type", sa.TEXT(), nullable=True)
    )
    op.add_column(
        "tariffs",
        sa.Column("vat_percentage", sa.NUMERIC(precision=5, scale=2), nullable=True),
    )
    op.drop_column("connectors", "current_price_per_kwh")
    op.drop_column("connectors", "pricing_kind")
    pricing_kind.drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_tariff_elements_tariff_id", table_name="tariff_elements")
    op.drop_table("tariff_elements")
