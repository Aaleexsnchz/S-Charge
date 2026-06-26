# Next steps — where to start

_Working handoff: just enough to resume tomorrow. Keep it small. When a "Now" item lands, delete it, update **State**, and pull the next item up._

## State (2026-06-26)

- **Phases:** 1–2 done · **3 dropped** · 4 slices 1–2 done (vehicle catalogue + PVPC on daily cron) **+ pricing/estimate service + `/api/simulate` + UI**, slices 3 & 5 pending · 5–8 not started. See [PLAN.md](PLAN.md).
- **Last change — pre-charge simulation (Slice 4).** `app/services/simulation.py` + `POST /api/simulate`: power = min(vehicle, connector), AC flat / DC taper above 80% SoC → energy, duration, cost (reuses the pricing service). UI is a "Simular carga" dialog on the point-detail page (`frontend/src/simulate/`). Model write-up: [thesis/simulacion-de-recarga.md](thesis/simulacion-de-recarga.md). 104 backend tests, frontend lint/build/vitest green. On branch `feat/backend-pricing-estimate-service`.
- **Prior — pricing/estimate service.** `app/services/pricing.py`: real REVE tariff else `PVPC(hour) + margin[AC 0.22 / DC 0.32]`. Ingest nulls implausible tariffs (`> 2 €/kWh`); live-DB garbage rows nulled.
- **Data:** REVE seed complete (seed-once, serve-from-DB); tariff refresh + PVPC both on daily cron.

## Now (immediate)

- [ ] **UI polish pass toward the final look** (next session) — bring the existing screens (home/dashboard, nav/layout, map, point detail, simulate dialog) closer to the intended end-state so progress is demonstrable to the tutor. Mobile-first, 360px reference. Concrete scope to be decided at the start of the session.
- [ ] **Synthetic availability** (Phase 4 Slice 3) — deterministic-seedable map occupancy; decide synthetic vs `unknown` (recommend synthetic, labelled illustrative).
- [ ] **B2 lifecycle rule** (ops) — in the Backblaze UI on `tfm-db-backups`: keep-last-version + delete-older-than-N-days. (Optional: rotate the B2 app key.)

**Deferred:** `/api/recommend` (Phase 4 Slice 5 — PVPC optimiser + algorithm write-up) is held until **after Phase 5 private points** land. The optimiser targets an *owned* point's charging schedule, so it gets a real home once private points exist; building it before then would have nowhere to attach.

## Remaining (project arc)

- **Phase 5** — private points, bookings, sessions + simulated wallet/ledger for paid use.
- **Phase 6** — responsive QA, error states, deploy at a real HTTPS domain + scaling/cost strategy.
- **Phase 7** — thesis writing, incl. business-plan, deployment and roadmap chapters ([thesis/indice.md](thesis/indice.md)).
- **Phase 8** — AI/agent assistant (candidate, time-gated; defense never depends on it).

Carry-forward invariants (price cascade, refresh watermark gotcha, availability model) live in [PLAN.md](PLAN.md) and [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md) / [thesis/planificacion-de-siembra.md](thesis/planificacion-de-siembra.md).

## Commands

```bash
docker compose exec backend uv run python -m scripts.refresh_reve --status   # refresh cursor state
docker compose exec backend uv run pytest -q                                 # backend tests
docker compose exec frontend sh -c "pnpm run lint && pnpm run build"         # frontend lint + build
```
