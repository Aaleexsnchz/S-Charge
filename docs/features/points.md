# Charging point catalogue

**Status:** ✅ Implemented · **Shipped in** [Phase 2](../phases/phase-2.md)

The Spanish charging network, mirrored from REVE into our own database and served as a nested OCPI-shaped structure: charging point → EVSE → connector. The connector carries the price, because a tariff shared across connectors of different power cannot carry one ([be-0003](../decisions/be-0003-price-on-the-connector.md)).

## Today

- **Backend** — `GET /api/points` (filters: `bbox`, `connector_standard`, `max_price_per_kwh`), `GET /api/points/{id}`, `GET /api/points/map` (slim GeoJSON for the map). Seeded and refreshed by `backend/scripts/seed_reve.py` and `refresh_reve.py` under REVE's 5 req/hr cap.
- **Frontend** — `features/points`: `/points/:id` renders operator, address, connectors with power, price and status, plus the simulation dialog and a Google Maps deep link.
- **Availability is not modelled.** `Evse.status` exists and `aggregate_status` rolls it up, but no source feeds it — see [plan.md](../plan.md) → Data strategy.

## Related

Data model chapter: [thesis/modelo-de-datos.md](../thesis/modelo-de-datos.md). Pricing and freshness: [thesis/precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md). Seed scheduling: [thesis/planificacion-de-siembra.md](../thesis/planificacion-de-siembra.md).

## Pending

- **The price model is stored but not yet shown.** `pricing_kind` distinguishes free, time-priced and unknown connectors, and the API serves it, but the UI still renders a bare number or an em dash — free chargers should say *gratis*, and a point should show which band the driver is in. [Phase 6](../phases/phase-6.md) Slice 6.
- **`aggregate_status` should default to `available`, not `unknown`,** when no `Evse.status` exists. Small backend change; the honesty note it depends on is already in [plan.md](../plan.md).
