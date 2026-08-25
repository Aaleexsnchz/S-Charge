# Charging point catalogue

**Status:** ✅ Implemented · **Shipped in** [Phase 2](../phases/phase-2.md)

The Spanish charging network, mirrored from REVE into our own database and served as a nested OCPI-shaped structure: charging point → EVSE → connector. The connector carries the price, because a tariff shared across connectors of different power cannot carry one ([be-0003](../decisions/be-0003-price-on-the-connector.md)).

## Today

- **Backend** — `GET /api/points` (filters: `bbox`, `connector_standard`, `max_price_per_kwh`), `GET /api/points/{id}` (adds `price_schedules`: the day's bands per connector, power-gated, one marked current), `GET /api/points/map` (slim GeoJSON for the map). Seeded and refreshed by `backend/scripts/seed_reve.py` and `refresh_reve.py` under REVE's 5 req/hr cap.
- **Frontend** — `features/points`: `/points/:id` renders operator, address, connectors with power, price and status, plus the simulation dialog and a Google Maps deep link.
- **Price variation by hour and by power are disjoint, and only one can be waited out.** 4% of priced connectors change price during the day and never more than six times; 11% vary by power, which is the difference between two connectors at the same station and is already visible in the connector list. The schedule table renders for the first group and disappears for everyone else.
- **The simulator prices the window, not the moment.** Each SoC step pays the band covering the minute its energy arrives, so a charge running from a day band into a cheaper night one is billed at both, and the result reports the effective price rather than any single band. A connector with no published price gets time and energy and no cost — never an estimate.
- **An absent price and a zero price read differently.** `features/points/display.ts` derives one `PricingState` per connector — a per-kWh amount, *gratis*, priced by time or by session, an expired tariff with the date it lapsed, or no published price — and every surface that shows a price renders it from there. Never an estimate: an invented number beside a real one is the objection [be-0002](../decisions/be-0002-availability-not-modelled.md) raises against simulated availability.
- **The catalogue drifts, the drift is measured, and the refresh repairs it.** About a quarter of every drained tariff page is a connector the mirror does not hold — **1,837** after one full drain, ~4 % growth in two and a half months. `reve_unmirrored_connectors` banks those with their tariff payload, and a `/locations` page that creates the connector settles its row in the same transaction, so the station arrives *priced* rather than blank for the ~243 days until its price next changes. The row count is the standing answer to how much of the catalogue is missing. `/cpos` and `/locations` share the tariff budget by priority rather than running on their own, so a catalogue catch-up can never delay a price.
- **The price schedule rides on the detail response, not on `ConnectorRead`.** `GET /api/points` takes a bbox and has **no limit**, so bands on the shared connector model would be resolved for every connector in a viewport to serve a list that displays none of them — the "resolve the price on every read" alternative [be-0003](../decisions/be-0003-price-on-the-connector.md) rejected. A `PointDetailRead` subclass keeps the cost on the one-point endpoint, where it measures 1–2 ms against that endpoint's 5 ms.
- **Price history cannot be recovered, and is not shown.** No REVE call shape returns a tariff's past values — the feed carries only what a connector costs now — so a price chart would have to be built from what this mirror happened to observe, starting at the seed. Nothing in the app reads it today.
- **Availability is not modelled.** `Evse.status` exists and `aggregate_status` rolls it up, but no source feeds it — see [plan.md](../plan.md) → Data strategy.

## Related

Data model chapter: [thesis/modelo-de-datos.md](../thesis/modelo-de-datos.md). Pricing and freshness: [thesis/precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md). Seed scheduling: [thesis/planificacion-de-siembra.md](../thesis/planificacion-de-siembra.md).

## Pending

- **`CONGESTION_TIME` bands are never priced.** 218 band rows carry a component type absent from REVE's published enum. It is a surcharge, so it never outranks `ENERGY`, `TIME` or `FLAT` and costs nothing today — but a connector whose only applicable band is one resolves to `unknown` and shows no price. Worth revisiting only if it becomes common.
- **`price` is ex-VAT per OCPI, and the app does not say so.** 4,017 of 5,513 band rows carry a `vat`, mostly `21.00` — but **192 write `0.21`**, the same rate as a fraction, so any correction has to normalise that first or it will under-charge those by 100×. Pre-existing, not introduced by the price model. The open question is whether the app shows what the driver pays or what the operator publishes; showing neither label is the current, unstated, answer.
- **`aggregate_status` should default to `available`, not `unknown`,** when no `Evse.status` exists. Small backend change; the honesty note it depends on is already in [plan.md](../plan.md).
