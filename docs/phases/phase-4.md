# Phase 4 — Simulation + Algorithm

> **Revision (2026-06-21) — ACN dropped.** Slice 3 no longer fits distributions on ACN; occupancy becomes a **lightweight synthetic** availability model (deterministic-seedable, illustrative only, not grounded in external data). Slices 4–5 lose all ACN-calibration language — `/api/simulate` is spec/physics-based and `/api/recommend` runs purely on the PVPC curve, so both are unblocked (no token). The phase is reframed from "the academic core" to a value-add feature; it still yields the algorithm chapter. See [PLAN.md](../PLAN.md) revision 2026-06-21.

> **Revision (2026-06-16).** PVPC history backfilled (2026-01-01 → today) via the existing `import_pvpc_prices`. Pricing strategy decided (input to Slices 4–5): serve the real REVE tariff; where none exists, estimate `PVPC(hour) + margin` with recommended defaults **AC +0.22 / DC +0.32 €/kWh** (derived from ~27k real tariffs vs PVPC), owner-overridable. Slice 2 still open: install the daily PVPC cron and add gap-backfill to `fetch_pvpc.py`. See [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).

Per [PLAN.md](../PLAN.md): vehicle catalogue, PVPC price ingest, and per-car pre-charge simulation. A value-add feature of the app (yields the algorithm chapter). `/api/simulate` is spec-based, no external dependency. **Phase 4 is complete** — Slice 3 (synthetic availability) is **dropped** and Slice 5 (`/api/recommend`) **moved to Phase 7**; see the slice notes below.

## Slice 1 — Vehicle catalogue

**Acceptance:** `vehicles` table seeded with ~30 common Spanish-market EVs (usable battery kWh, max AC kW, max DC kW, DC connector standard); `GET /api/vehicles` returns the catalogue ordered for a picker UI. Seed is idempotent (`python -m scripts.seed_vehicles`).

- [x] `Vehicle` model + Alembic migration
- [x] `seed_vehicles.py` idempotent seed with curated spec list (public spec-sheet data; 31 EVs)
- [x] `GET /api/vehicles` + route test
- [x] Seed idempotency (ON CONFLICT upsert keyed on make+model; verified by re-run)

## Slice 2 — PVPC price ingest

**Acceptance:** hourly PVPC prices land in `electricity_prices` via `python -m scripts.fetch_pvpc` against REE's public API (`apidatos.ree.es`, no token); the script fetches today + tomorrow (tomorrow publishes ~20:15 CET) and is safe to re-run; a daily cron line keeps prices fresh (same operating pattern as the REVE seed). `GET /api/prices/today` serves the curve for the optimiser UI.

- [x] `ReeClient` async client for `apidatos.ree.es` (PVPC indicator), tested with pytest-httpx. Real-world findings baked in: the hourly PVPC series (id 1001) publishes with a lag (current day fills in during the day; REE answers **500** for unpublished days), so the script fetches a yesterday/today/tomorrow window and treats 5xx as "not published yet"
- [x] `electricity_prices` model + migration (hour timestamp unique, €/kWh)
- [x] Idempotent `import_pvpc_prices` ETL + `fetch_pvpc.py` script (verified live: 24 prices for 2026-06-12, 0.072–0.272 €/kWh)
- [x] `GET /api/prices/today` (+ `?day=`, Madrid-local) + route tests
- [ ] Daily cron line installed → **moves to Phase 6** (runs on the deployment server, not the laptop)

## Slice 3 — Synthetic availability simulation — DROPPED (2026-06-28)

Removed. Live availability is **not modelled** — REVE has no constant status feed, so points show as **available by default** (illustrative); occupancy appears only for any artificial demo data added before the defense. The status plumbing (`Evse.status`, the `aggregate_status` rollup, marker colours) stays and supports a real source later. See [PLAN.md](../PLAN.md) Data strategy and [features.md](../features.md).

## Slice 4 — `/api/simulate` + UI — done

**Acceptance:** given vehicle + connector (+ initial/target SoC), returns predicted duration, energy and cost (tariff from the point, or PVPC+margin/fixed for user points later); the UI renders the predicted session in Spanish.

- [x] Simulation service: power = min(vehicle, connector), AC/DC aware, simple taper above 80% SoC for DC
- [x] `POST /api/simulate` + tests (happy path, AC vs DC, taper, cost)
- [x] Simulation UI: vehicle picker, point/connector context, results metrics

Deviations from the original spec: shipped as a **dialog on point detail** (not a standalone `/simulate` route); the **charging-curve chart is deferred** — the model can produce a real power-vs-SoC curve (a small `/api/simulate` addition + MUI X Charts), so it's a genuine enhancement to revisit, not a mock.

## Slice 5 — `/api/recommend` (smart home charging) — MOVED to Phase 7

Moved out of Phase 4: the optimiser targets an **owned** point's schedule, so it needs private points (Phase 7) to attach to. Acceptance unchanged — see [PLAN.md](../PLAN.md) Phase 7.
