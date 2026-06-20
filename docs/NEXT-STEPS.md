# Next steps — where to start

_Working handoff. Updated 2026-06-16. Living doc; trim as items close._

## Current state

- **Branch:** `feat/reve-seed`. This session's work is **uncommitted** but verified (backend: ruff + mypy + 80 tests pass; frontend: eslint + `tsc` pass).
- **REVE seed:** still running on the hourly cron (minute 30). `/cpos` and `/locations` complete; `/connectors/tariffs` mid-run (~page 291). No operational-status endpoint anymore — seed finishes once tariffs complete.
- **PVPC:** history backfilled 2026-01-01 → today (~4,000 hourly rows). Daily refresh **not yet on cron**.
- **Pricing model:** decided, not yet built (see below). Margin defaults from real data: **AC +0.22, DC +0.32 €/kWh** over the ~0.12 €/kWh PVPC reference.

## Decisions locked this session

- REVE is a **seed-once, serve-from-DB** mirror; user clicks never hit REVE. Real tariff is the price; staleness is shown with a date.
- **Operational status** (working/broken) → assumed always operational, not modelled. **Availability** (free/in use) → `status` column on the EVSE, **simulated** in Phase 4 (the per-EVSE `/evses/{id}/status` endpoint is deliberately not called).
- Price cascade: **stored REVE tariff → else `PVPC(hour) + margin[charge_type]`** labelled *estimado*. Owners set their own price/margin; the margin is only the recommended default.
- Post-seed freshness via **incremental refresh** (`refresh_reve.py`), windowed + resumable; cheap because daily change volume (tens–hundreds) is far below the ~12k/day capacity.
- Full rationale: [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md), [thesis/seed-scheduling.md](thesis/seed-scheduling.md).

## Start here tomorrow (in order)

1. **Check the seed.** `docker compose exec backend uv run python -m scripts.seed_reve --status`. When `/connectors/tariffs` shows `completed`, **switch the cron** from `scripts.seed_reve` to `scripts.refresh_reve` (one word; `crontab -e`). `refresh_reve` no-ops until then, so the switch is safe anytime.
2. **PVPC daily cron + gap-backfill.** Install the `fetch_pvpc` daily cron line and change `fetch_pvpc.py` to backfill any gap since the last stored hour (so WSL-idle days self-heal). Closes the last open bullet of Phase 4 Slice 2.
3. **Pricing/estimate service.** `estimate_price(connector, hour) = PVPC(hour) + margin[AC|DC]` with the two default constants; reused by `/api/simulate` and (Phase 5) owner public-point pricing. Quick data-hygiene fix at the same time: filter the garbage tariff (one row at 8676 €/kWh) and the 48 null prices at ingest.
4. **Phase 4 core (the academic part).** Needs the real ACN import (`ACN_API_TOKEN`): distribution fitting → availability simulation writing EVSE `status` → `/api/simulate` → `/api/recommend`. See [phases/phase-4.md](phases/phase-4.md) Slices 3–5.

## Open TODOs

- [ ] Switch cron seed → refresh once the seed completes
- [ ] `fetch_pvpc.py`: gap-backfill + daily cron line (Phase 4 Slice 2)
- [ ] Pricing/estimate service + tariff ingest hygiene (outlier/null guard)
- [ ] Phase 4 Slices 3–5 (fitting, simulation, simulate, recommend) — gated on ACN token

## Suggested commits (this session)

1. `feat(backend): post-seed incremental REVE refresh; drop operational-status endpoint` — `seed_reve.py`, `etl/reve.py`, `etl/cursor.py`, `models/etl.py`, `scripts/refresh_reve.py`, migration `4702…`, ETL tests.
2. `feat: model EVSE availability as status (replaces is_operational)` — `models/charging_point.py`, `services/points.py`, `schemas/point.py`, migration `71cc…`, points tests, frontend (`map/*`, `points/*`, regenerated `schema.d.ts`).
3. `docs: pricing & catalogue-freshness strategy; update plan/phases/next-steps` — new thesis chapter, `seed-scheduling.md`, `PLAN.md`, `README.md`, `phase-2.md`, `phase-4.md`, this file.

## Useful commands

```bash
docker compose exec backend uv run python -m scripts.seed_reve --status      # seed progress (no API call)
docker compose exec backend uv run python -m scripts.refresh_reve --status   # refresh cursor state
docker compose exec backend uv run pytest -q                                 # backend tests
docker compose exec frontend sh -c "pnpm lint && pnpm exec tsc --noEmit"      # frontend checks
tail -n 20 ~/.reve-seed.log                                                   # cron tick log
```
