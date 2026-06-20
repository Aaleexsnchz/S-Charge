# Next steps — where to start

_Working handoff. Updated 2026-06-20. Living doc; trim as items close._

## Current state

- **Branch:** `feat/reve-seed`. The work from the last session is **committed** (`ad4b466` incremental refresh + drop operational-status, `7ea6ea8` EVSE availability as status, `8e48d8f` pricing/freshness docs). Pre-commit gate (backend `ruff` + `basedpyright`; frontend Biome + `tsc`) passed at commit time; 80 backend tests.
- **REVE seed: complete.** All three endpoints finished — `/cpos` (2026-06-07), `/locations` (2026-06-09), `/connectors/tariffs` (2026-06-19 09:30 UTC). The seed-once mirror is fully populated.
- **REVE refresh: not yet cycled.** `refresh_reve`'s cursor still mirrors the seed pages with no watermark — the cron has not been switched from seed → refresh yet (see Start here #1).
- **PVPC:** 4,007 hourly rows, latest hour `2026-06-16 21:00 UTC` — **~4 days stale**. Daily refresh still **not on cron**, and the gap since 06-16 is exactly the WSL-idle hole the gap-backfill is meant to self-heal.
- **Pricing model:** decided, not yet built (see below). Recommended margin defaults over the PVPC reference are calibrated in [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md) — use that as the source of truth rather than re-stating the constants here.

## Locked decisions (carry-forward)

- REVE is a **seed-once, serve-from-DB** mirror; user clicks never hit REVE. Real tariff is the price; staleness is shown with a date.
- **Operational status** (working/broken) → assumed always operational, not modelled. **Availability** (free/in use) → `status` column on the EVSE, **simulated** in Phase 4 (the per-EVSE `/evses/{id}/status` endpoint is deliberately not called).
- Price cascade: **stored REVE tariff → else `PVPC(hour) + margin[charge_type]`** labelled *estimado*. Owners set their own price/margin; the margin is only the recommended default.
- Post-seed freshness via **incremental refresh** (`refresh_reve.py`), windowed + resumable; cheap because daily change volume (tens–hundreds) is far below the ~12k/day capacity.
- Full rationale: [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md), [thesis/seed-scheduling.md](thesis/seed-scheduling.md).

## Start here (in order)

1. **Switch the cron seed → refresh.** The seed is complete, so this is now actionable: change the hourly cron line from `scripts.seed_reve` to `scripts.refresh_reve` (`crontab -e`). Confirm the first cycle lands a watermark with `python -m scripts.refresh_reve --status`.
2. **PVPC daily cron + gap-backfill.** Install the `fetch_pvpc` daily cron line and change `fetch_pvpc.py` to backfill any gap since the last stored hour — there's a real 2026-06-16 → now hole to heal. Closes the last open bullet of Phase 4 Slice 2.
3. **Pricing/estimate service.** `estimate_price(connector, hour) = PVPC(hour) + margin[AC|DC]` with the two default constants; reused by `/api/simulate` and (Phase 5) owner public-point pricing. Quick data-hygiene fix at the same time: filter the garbage tariff (one row at 8676 €/kWh) and the 48 null prices at ingest.
4. **Phase 4 core (the academic part).** Needs the real ACN import (`ACN_API_TOKEN`): distribution fitting → availability simulation writing EVSE `status` → `/api/simulate` → `/api/recommend`. See [phases/phase-4.md](phases/phase-4.md) Slices 3–5.

## Open TODOs

- [ ] Switch cron seed → refresh (seed is complete — do this first)
- [ ] `fetch_pvpc.py`: gap-backfill + daily cron line; heal the 06-16 → now gap (Phase 4 Slice 2)
- [ ] Pricing/estimate service + tariff ingest hygiene (outlier/null guard)
- [ ] Phase 4 Slices 3–5 (fitting, simulation, simulate, recommend) — gated on ACN token

## Useful commands

```bash
docker compose exec backend uv run python -m scripts.seed_reve --status      # seed progress (no API call)
docker compose exec backend uv run python -m scripts.refresh_reve --status   # refresh cursor state
docker compose exec backend uv run pytest -q                                 # backend tests
docker compose exec frontend sh -c "pnpm run lint && pnpm run build"         # frontend lint + typecheck/build
tail -n 20 ~/.reve-seed.log                                                   # cron tick log
```
