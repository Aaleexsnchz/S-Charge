---
id: be-0003
status: accepted
phase: 6
date: 2026-08
related: [be-0001]
---

# be-0003: Store the tariff's price bands, and resolve the price on the connector

**Decision.** The `elements` array REVE publishes with every tariff is stored as queryable rows in **`tariff_elements`** — one row per OCPI price component, carrying the restrictions of the element that holds it. The single `tariffs.price_per_kwh` column is **dropped**, not redefined, along with the `price_component_type`, `vat_percentage` and `step_size` columns flattened from the same place. What a driver pays now lives on **`connectors.current_price_per_kwh`**, beside a **`connectors.pricing_kind`** of `energy · time · flat · free · unknown`, recomputed hourly.

**Rationale.** The ETL took the first `ENERGY` component it met and discarded the restrictions. That is wrong in two independent ways, and only the second is fatal.

Price varies by **time of day**: a measured tariff prices 0.25 €/kWh overnight and 0.29 during the day. Storing the first band is merely imprecise — a better choice of band would fix it.

Price also varies by **connector power**, and this one cannot be fixed by choosing better. The same measured tariff prices 0.29, 0.37 and 0.47 €/kWh for the same hour depending on whether the connector is rated up to 22, 100 or 450 kW. **7,175 of the 41,963 priced connectors sit on a tariff that publishes more than one energy price**, and those tariffs are shared across connectors of different power. One number on the tariff row is not an approximation of those; there is no number that could be right for all of them. The grain at which the answer is unique is the connector, and every connector has `max_electric_power` populated, so it always resolves.

Nothing had to be re-fetched to fix it: all 2,126 stored tariffs already held their complete `elements` array in `raw_data`, because the flattening happened on the way out, never on the way in.

**Consequences.**

- **An absent price is never filled in with an estimate.** `pricing_kind` separates *free* (the source published a price and it is zero) from *unknown* (the source published nothing), and only the first is a claim about the world. The `PVPC + margen` estimate is not shown for the second: it stays as the recommended default offered to an owner pricing their own point, where it is a suggestion rather than an attribution. Same objection as [be-0002](be-0002-availability-not-modelled.md) — a plausible number a user reads as real is worse than an empty field.
- **`price_per_kwh IS NULL` no longer conflates four different facts**, and separating them refuted the belief that prompted this work. The flattened model showed 1,152 connectors with no per-kWh price and they were read as *free*. As rows, 1,144 of them carry a lone `FLAT 0.0` with no VAT, `step_size` 0 and **no energy band at all** — an unfilled record. The CPOs publishing them price the rest of their estate normally, which is the tell. **30 connectors are genuinely free**, each an explicit `ENERGY 0.0` fully populated. Free has to be a claim the source made, not the absence of one, or the app sends drivers to chargers that bill them.
- **An expired tariff no longer prices anything, and says so.** 2,138 connectors were priced from a tariff past its own `valid_to`, and those average 0.1129 €/kWh against 0.3517 for live ones — ended promotions rather than unmaintained defaults. 2,115 arrived already expired, so REVE serves them as current regardless. The app shows *the published tariff expired on 12/08/2026* rather than a bare dash: stale is a different fact from absent, and saying which one it is costs nothing and asserts no price. `valid_to` stays on the API response for that reason.
- **A stale mirror can now say "no price" rather than a wrong one, and the tariff's own fallback usually stops it having to.** 1,532 connectors sit on a *dated* schedule — a band per quarter-hour, valid for one named day — and all of those bands have expired. The unrestricted band in the same tariff still prices 1,485 of them; the 47 without one resolve to `unknown`, which is the honest answer. Under the old model they all kept serving whatever price the first band happened to carry.
- **`current_price_per_kwh` is a denormalisation and goes stale between recomputes.** It is refreshed on the hourly ETL tick, which is also the rate at which the band it summarises can change. Anything that needs a different instant reads `tariff_elements` directly, which is how the simulator prices a charging window that crosses a boundary.
- **A restriction of `0` has to be read as "not set", and the most specific band has to win.** REVE emits `0` rather than omitting a bound, and a literal reading is destructive: `max_power = 0` matches no connector, and `min_duration = 0` looks session-gated when it gates nothing. Separately, 127 tariffs list an unrestricted fallback band alongside the real windows, so resolving in source order hands 1,247 connectors the fallback price inside a window meant to be cheaper. Both cost real prices — 797 connectors resolved to `unknown` that did not need to — and neither is visible until the bands are stored as rows and can be counted.
- The resolver runs as one SQL statement over every connector, and the backfill migration carries a frozen copy of it. The duplication is deliberate: a migration that imported the live function would break `alembic upgrade head` the day that function's shape changed.

**Rejected alternatives.**

- *Keep one price on the tariff, but pick a better band.* Fixes the time axis and leaves the power axis structurally broken for 7,175 connectors. It also has no honest answer to "which band?" without knowing the connector.
- *Resolve the price on every read instead of denormalising it.* Correct by construction and needs no recompute, but the map's price filter and its `min()` aggregate would each have to evaluate the band logic across ~47,000 connectors per request. The band changes on the hour; an hourly recompute matches it exactly.
- *Leave the bands in `raw_data` and parse them in Python when needed.* No migration and no new table. Rejected: the price filter is a database query, and a filter that cannot be expressed in SQL becomes a full table scan through the ORM.
- *Store only the restrictions the resolver uses today.* Would have dropped `min_kwh`, the current limits and the session durations. Rejected on [be-0001](be-0001-reve-mirror-not-proxy.md)'s own principle — the mirror stores what the source publishes, and the simulator, which knows the session, can answer what the "price now" resolver cannot.

**References.**

- [thesis/precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md) — the measurements behind the numbers here.
- [be-0001](be-0001-reve-mirror-not-proxy.md) — mirror, not proxy.
