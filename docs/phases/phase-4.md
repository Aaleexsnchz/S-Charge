# Phase 4 — Simulation + Algorithm

> **Revision (2026-06-21) — ACN dropped.** Slice 3 no longer fits distributions on ACN; occupancy becomes a **lightweight synthetic** availability model (deterministic-seedable, illustrative only, not grounded in external data). Slices 4–5 lose all ACN-calibration language — `/api/simulate` is spec/physics-based and `/api/recommend` runs purely on the PVPC curve, so both are unblocked (no token). The phase is reframed from "the academic core" to a value-add feature; it still yields the algorithm chapter. See [PLAN.md](../PLAN.md) revision 2026-06-21.

> **Revision (2026-06-16).** PVPC history backfilled (2026-01-01 → today) via the existing `import_pvpc_prices`. Pricing strategy decided (input to Slices 4–5): serve the real REVE tariff; where none exists, estimate `PVPC(hour) + margin` with recommended defaults **AC +0.22 / DC +0.32 €/kWh** (derived from ~27k real tariffs vs PVPC), owner-overridable. Slice 2 still open: install the daily PVPC cron and add gap-backfill to `fetch_pvpc.py`. See [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).

Per [PLAN.md](../PLAN.md): vehicle catalogue, PVPC price ingest, a lightweight synthetic availability model, per-car pre-charge simulation, smart home-charging optimiser. A value-add feature of the app (yields the algorithm chapter). No external dependency — `/api/simulate` is spec-based and `/api/recommend` runs on the PVPC curve; the original ACN-calibration plan (Slice 3) is superseded per the revision note above.

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
- [ ] Daily cron line installed + documented in thesis seed-scheduling chapter

## Slice 3 — Synthetic availability simulation

> Reframed 2026-06-21: no ACN. A lightweight synthetic model replaces distribution fitting; presented as illustrative only.

**Acceptance:** a deterministic-seedable simulator drives per-EVSE availability from a simple synthetic model (e.g. time-of-day utilisation curve + seeded noise) so the map shows live-looking occupancy; the model is reproducible and clearly labelled as illustrative, not grounded in real data.

- [ ] Synthetic availability service (time-of-day utilisation; deterministic seed)
- [ ] Occupancy simulator mapping utilisation to REVE/user EVSEs; map `aggregate_status` reflects it
- [ ] Unit tests on the seeded model; brief write-up notes for the thesis

## Slice 4 — `/api/simulate` + UI

**Acceptance:** given vehicle + connector (+ initial/target SoC), returns predicted duration, energy and cost (tariff from the point, or PVPC+margin/fixed for user points later); `/simulate` page renders the predicted session (charging curve approximation) in Spanish.

- [ ] Simulation service: power = min(vehicle, connector), AC/DC aware, simple taper above 80% SoC for DC
- [ ] `POST /api/simulate` + tests (happy path, AC vs DC, taper, cost)
- [ ] `/simulate` lazy route: vehicle picker, point/connector context, results card + chart

## Slice 5 — `/api/recommend` (smart home charging)

**Acceptance:** given a charging power, vehicle, energy needed and departure time, returns the cheapest contiguous-or-split schedule over tonight's PVPC curve plus 1–2 alternatives with savings vs charging immediately; algorithm written up for the thesis.

- [ ] Recommendation service (greedy over hourly PVPC slots; contiguous and split variants)
- [ ] `POST /api/recommend` + tests
- [ ] 1–2 page algorithm write-up (Spanish) in docs/thesis/
