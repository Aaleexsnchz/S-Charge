# Next steps — where to start

_Working handoff: just enough to resume tomorrow. Keep it small. When a "Now" item lands, delete it, update **State**, and pull the next item up._

## State (2026-06-21)

- **Phases:** 1–2 done · **3 dropped** · 4 slices 1–2 done (vehicle catalogue + PVPC on daily cron), slices 3–5 pending · 5–8 not started. See [PLAN.md](PLAN.md).
- **Last change — scope pivot.** The thesis core is now the **application itself**; the optimiser and AI are value-add features. ACN dropped (code + table deleted, `drop acn_sessions` migration applied); docs re-pointed; thesis files renamed to Spanish + outline in [thesis/indice.md](thesis/indice.md); deferred ideas in [ideas-backlog.md](ideas-backlog.md). On branch `chore/drop-acn-scope-pivot`, staged for review. Backend 76 tests green.
- **Data:** REVE seed complete (seed-once, serve-from-DB); tariff refresh + PVPC both on daily cron.

## Now (immediate)

- [ ] **Pricing/estimate service** — `estimate_price(connector, hour) = PVPC(hour) + margin[AC|DC]`; reused by `/api/simulate` and owner pricing. Same pass: drop the 8676 €/kWh outlier tariff + 48 null prices at ingest.
- [ ] **`/api/simulate` + UI** (Phase 4 Slice 4) — spec-based: power = min(vehicle, connector), AC/DC taper → duration, energy, cost.
- [ ] **`/api/recommend`** (Phase 4 Slice 5) — cheapest schedule over tonight's PVPC curve + alternatives; algorithm write-up.
- [ ] **Synthetic availability** (Phase 4 Slice 3) — deterministic-seedable map occupancy; decide synthetic vs `unknown` (recommend synthetic, labelled illustrative).
- [ ] **B2 lifecycle rule** (ops) — in the Backblaze UI on `tfm-db-backups`: keep-last-version + delete-older-than-N-days. (Optional: rotate the B2 app key.)

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
