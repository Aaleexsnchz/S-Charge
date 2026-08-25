# Charging point catalogue

**Status:** ✅ Implemented · **Shipped in** [Phase 2](../phases/phase-2.md)

The Spanish charging network, mirrored from REVE into our own database and served as a nested OCPI-shaped structure: charging point → EVSE → connector. The connector carries the price, because a tariff shared across connectors of different power cannot carry one ([be-0003](../decisions/be-0003-price-on-the-connector.md)).

## Today

- **Backend** — `GET /api/points` (filters: `bbox`, `connector_standard`, `max_price_per_kwh`), `GET /api/points/{id}` (adds `price_schedules`: the day's bands per connector, power-gated, one marked current), `GET /api/points/map` (slim GeoJSON for the map). Seeded and refreshed by `backend/scripts/seed_reve.py` and `refresh_reve.py` under REVE's 5 req/hr cap.
- **Frontend** — `features/points`: `/points/:id` renders operator, address, connectors with power, price and status, plus the simulation dialog and a Google Maps deep link.
- **Price variation by hour and by power are disjoint, and only one can be waited out.** 4% of priced connectors change price during the day and never more than six times; 11% vary by power, which is the difference between two connectors at the same station and is already visible in the connector list. The schedule table renders for the first group and disappears for everyone else.
- **The simulator prices the window, not the moment.** Each SoC step pays the band covering the minute its energy arrives, so a charge running from a day band into a cheaper night one is billed at both, and the result reports the effective price rather than any single band. A connector with no published price gets time and energy and no cost — never an estimate.
- **An absent price and a zero price read differently.** `features/points/display.ts` derives one `PricingState` per connector — a per-kWh amount, *gratis*, priced by time or by session, an expired tariff with the date it lapsed, or no published price — and every surface that shows a price renders it from there. Never an estimate: an invented number beside a real one is the objection [be-0002](../decisions/be-0002-availability-not-modelled.md) raises against simulated availability.
- **The catalogue drifts, and the drift is measured.** `/cpos` and `/locations` are frozen at the June 2026 seed; only tariffs are refreshed, because refreshing the catalogue would starve the tariff budget. About a quarter of every drained tariff page is a connector the mirror does not hold — ~1,900 over one drain, ~4 % growth in two and a half months. `reve_unmirrored_connectors` banks those with their tariff payload so a later repair pass can import them *priced*; its row count is the standing answer to how much of the catalogue is missing.
- **Availability is not modelled.** `Evse.status` exists and `aggregate_status` rolls it up, but no source feeds it — see [plan.md](../plan.md) → Data strategy.

## Related

Data model chapter: [thesis/modelo-de-datos.md](../thesis/modelo-de-datos.md). Pricing and freshness: [thesis/precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md). Seed scheduling: [thesis/planificacion-de-siembra.md](../thesis/planificacion-de-siembra.md).

## Pending

- **`aggregate_status` should default to `available`, not `unknown`,** when no `Evse.status` exists. Small backend change; the honesty note it depends on is already in [plan.md](../plan.md).
