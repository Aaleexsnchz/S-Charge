# Phase 3 — Simulation + algorithm

Per [plan.md](../plan.md): vehicle catalogue, PVPC price ingest, and per-car pre-charge simulation. A value-add feature of the app that also yields the thesis's algorithm chapter. `/api/simulate` is spec-based — no external dependency at request time.

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Vehicle catalogue | Done | #6 |
| 2 | PVPC price ingest | Done | #6 |
| 3 | `/api/simulate` + UI | Done | direct to `main` |

**Pricing rule set here and used from Phase 8 on:** serve the real REVE tariff; where none exists, estimate `PVPC(hour) + margin`, recommended defaults **AC +0.22 / DC +0.32 €/kWh** (derived from ~27k real tariffs vs PVPC), owner-overridable. Detail: [the thesis](../../thesis/S-Charge-TFM.pdf).

## Slice 1 — Vehicle catalogue

**Acceptance:** `vehicles` table seeded with ~30 common Spanish-market EVs (usable battery kWh, max AC kW, max DC kW, DC connector standard); `GET /api/vehicles` returns the catalogue ordered for a picker UI. Seed is idempotent (`python -m scripts.seed_vehicles`).

- [x] `Vehicle` model + Alembic migration
- [x] `seed_vehicles.py` idempotent seed with curated spec list (public spec-sheet data; 31 EVs)
- [x] `GET /api/vehicles` + route test
- [x] Seed idempotency (ON CONFLICT upsert keyed on make+model; verified by re-run)

## Slice 2 — PVPC price ingest

**Acceptance:** hourly PVPC prices land in `electricity_prices` via `python -m scripts.fetch_pvpc` against REE's public API (`apidatos.ree.es`, no token); the script fetches today + tomorrow (tomorrow publishes ~20:15 CET) and is safe to re-run. `GET /api/prices/today` serves the curve.

- [x] `ReeClient` async client for `apidatos.ree.es` (PVPC indicator), tested with pytest-httpx. The hourly PVPC series (id 1001) publishes with a lag — the current day fills in during the day and REE answers **500** for unpublished days — so the script fetches a yesterday/today/tomorrow window and treats 5xx as "not published yet"
- [x] `electricity_prices` model + migration (hour timestamp unique, €/kWh)
- [x] Idempotent `import_pvpc_prices` ETL + `fetch_pvpc.py` script
- [x] `GET /api/prices/today` (+ `?day=`, Madrid-local) + route tests
- [x] History backfilled (2026-01-01 → today)
- [x] Daily schedule — runs in the `scheduler` container, provisioned in [Phase 5](phase-5.md)

## Slice 3 — `/api/simulate` + UI

**Acceptance:** given vehicle + connector (+ initial/target SoC), returns predicted duration, energy and cost (tariff from the point, or PVPC + margin / fixed for user points); the UI renders the predicted session in Spanish.

- [x] Simulation service: power = min(vehicle, connector), AC/DC aware, simple taper above 80% SoC for DC
- [x] `POST /api/simulate` + tests (happy path, AC vs DC, taper, cost)
- [x] Simulation UI: vehicle picker, point/connector context, results metrics — shipped as a dialog on point detail rather than a standalone `/simulate` route

**Deferred enhancement:** a power-vs-SoC charging-curve chart. The model can already produce the curve; it needs a small `/api/simulate` addition plus a chart component. Tracked in [features/simulation.md](../../features/simulation.md).
