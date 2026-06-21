# Next steps — where to start

_Working handoff. Updated 2026-06-21. Living doc; trim as items close._

## Current state

- **Branch:** merged. PR #6 (`feat/reve-seed`) merged to `main` on 2026-06-21 (merge `fa60fc1`); branch deleted. **Start new work from `main` on a fresh branch.** CI green (backend `ruff` + `basedpyright` + `pytest`; frontend Biome + `vitest` + build); 85 backend tests.
- **REVE seed: complete.** All three endpoints finished — `/cpos` (2026-06-07), `/locations` (2026-06-09), `/connectors/tariffs` (2026-06-19 09:30 UTC). The seed-once mirror is fully populated.
- **REVE refresh: cron switched + scoped to tariffs (2026-06-21).** The hourly cron runs `scripts.refresh_reve`, now refreshing **only `/connectors/tariffs`** (prices). `/cpos` and `/locations` are dropped from the refresh — the catalogue is frozen at the seed snapshot (no price data; new post-seed stations won't appear, accepted trade-off). All 5 calls/tick go to draining tariffs.
- **PVPC: healed + on cron (2026-06-21).** `fetch_pvpc.py` now backfills every day from the last stored hour through tomorrow (`MAX_BACKFILL_DAYS=60` guard); the 06-16→06-21 hole is filled, and a daily `09:00` Madrid cron line keeps it fresh (tomorrow's curve is published by REE ~20:15 CET the evening before, so 09:00 always has it).
- **Pricing model:** decided, not yet built (see below). Recommended margin defaults over the PVPC reference are calibrated in [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md) — use that as the source of truth rather than re-stating the constants here.

## Locked decisions (carry-forward)

- REVE is a **seed-once, serve-from-DB** mirror; user clicks never hit REVE. Real tariff is the price; staleness is shown with a date.
- **Operational status** (working/broken) → assumed always operational, not modelled. **Availability** (free/in use) → `status` column on the EVSE, **simulated** in Phase 4 (the per-EVSE `/evses/{id}/status` endpoint is deliberately not called).
- Price cascade: **stored REVE tariff → else `PVPC(hour) + margin[charge_type]`** labelled *estimado*. Owners set their own price/margin; the margin is only the recommended default.
- Post-seed freshness via **incremental refresh** (`refresh_reve.py`), windowed + resumable, **tariffs-only** (prices are the only thing worth refreshing; catalogue stays at the seed snapshot); cheap because daily change volume (tens–hundreds) is far below the ~12k/day capacity.
- **Seed→refresh handoff gotcha:** the first refresh `date_from` must be `min(tariffs.last_refreshed_at)` (oldest captured page), **not** `completed_at`. A budgeted seed paginates over days, so completion time understates the window and skips prices changed mid-seed. Re-seeding? Re-set the watermark to the oldest capture before the first refresh tick (`UPDATE reve_etl_cursor SET refresh_watermark = (SELECT min(last_refreshed_at) FROM tariffs), refresh_cycle_end = NULL, next_page = 1 WHERE endpoint = '/connectors/tariffs';`).
- Full rationale: [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md), [thesis/seed-scheduling.md](thesis/seed-scheduling.md).

## Start here (in order)

1. **Pricing/estimate service.** `estimate_price(connector, hour) = PVPC(hour) + margin[AC|DC]` with the two default constants; reused by `/api/simulate` and (Phase 5) owner public-point pricing. Quick data-hygiene fix at the same time: filter the garbage tariff (one row at 8676 €/kWh) and the 48 null prices at ingest.
2. **Full ACN import** (`ACN_API_TOKEN`). The single critical unblock — feeds both Phase 3's notebook and Phase 4's distribution fitting. `docker compose exec backend uv run python -m scripts.import_acn` (~31k rows/site, resumable; server caps 100/page).
3. **Phase 4 core (the academic part).** Distribution fitting → availability simulation writing EVSE `status` → `/api/simulate` → `/api/recommend`. See [phases/phase-4.md](phases/phase-4.md) Slices 3–5.

## Done 2026-06-21

- [x] Switched the hourly cron `scripts.seed_reve` → `scripts.refresh_reve` (seed complete).
- [x] `fetch_pvpc.py` gap-backfill (last stored hour → tomorrow) + daily `09:00` Madrid cron line; healed the 06-16 → 06-21 hole. Closes Phase 4 Slice 2.
- [x] Seeded the first tariff refresh watermark to `min(last_refreshed_at)` = `2026-06-10 09:30` (oldest capture), not `completed_at` = `2026-06-19`. The budgeted seed is non-atomic (pages captured across ~9 days), so starting the first refresh at completion would skip any price that changed during the seed. Added a `changed` field to the `reve_etl_tariffs` audit line (genuine source changes vs. unconditional re-fetches).
- [x] DB backups: `scripts/backup_db.sh` + weekly `scripts/backup_db_cron.sh` (Mon 09:00 Madrid) → Backblaze B2 (`tfm-db-backups`), seed-only/PII-safe; restore verified end-to-end. See [DOCKER.md](DOCKER.md).

## Open TODOs

- [ ] **B2 lifecycle rule** — set in the Backblaze UI on `tfm-db-backups`: *keep only the last version* + *delete files older than N days*, so versions hidden by the weekly prune don't accumulate. (Optional: rotate the B2 app key — it was pasted into chat during setup.)
- [ ] Pricing/estimate service + tariff ingest hygiene (outlier/null guard)
- [ ] Full ACN import (`ACN_API_TOKEN`) — unblocks Phases 3 and 4
- [ ] Phase 4 Slices 3–5 (fitting, simulation, simulate, recommend) — gated on ACN token

## Before next session — ACN decisions to think through

The ACN import is the critical unblock for Phases 3 and 4. Worth deciding _before_ diving in, not mid-flight:

- **Token + scope.** `ACN_API_TOKEN` must be set first. Which sites — Caltech, JPL, Office001 — and all of them or one to start? Full import is ~31k rows/site, resumable (server caps 100/page). So far only a 100-row smoke run exists.
- **What we actually model.** ACN gives real sessions (arrival time, plug duration, energy delivered). Decide which distributions to fit and at what granularity: arrivals (by hour × day-of-week?), session duration, energy — and how those map onto simulated per-EVSE availability `status`.
- **Phase 3 vs Phase 4 boundary.** Phase 3 = import + data-validation doc + thesis notebook (figures/conclusions). Phase 4 = fit distributions → drive simulated availability + `/api/simulate` + `/api/recommend`. The import feeds both — do it once, cleanly, with row-count validation against the source.
- **Framing.** ACN is internal modelling data, never user-facing; the notebook is thesis material, not an app screen. Keep that boundary when shaping the import schema.
- Specs: [phases/phase-3.md](phases/phase-3.md), [phases/phase-4.md](phases/phase-4.md).

## Useful commands

```bash
docker compose exec backend uv run python -m scripts.seed_reve --status      # seed progress (no API call)
docker compose exec backend uv run python -m scripts.refresh_reve --status   # refresh cursor state
docker compose exec backend uv run pytest -q                                 # backend tests
docker compose exec frontend sh -c "pnpm run lint && pnpm run build"         # frontend lint + typecheck/build
tail -n 20 ~/.reve-seed.log                                                   # cron tick log
```
