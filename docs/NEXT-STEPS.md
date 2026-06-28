# Next steps — where to start

_Working handoff: just enough to resume tomorrow. Keep it small. When a "Now" item lands, delete it, update **State**, and pull the next item up._

## State (2026-06-28)

- **Phases (renumbered 2026-06-28):** 1–2 done · 3 dropped · **4 done** (Slice 3 synthetic availability dropped; Slice 5 `/api/recommend` → Phase 7) · **5 done** (frontend redesign + IA) · **6 in progress** (deployment + CI/CD + releases → v1.0.0) · 7 features+optimiser · 8 AI (planned, TBD) · 9 polish/security/scaling · 10 thesis. See [PLAN.md](PLAN.md).
- **Last change — frontend redesign + IA restructure.** Adopted the `s-charge` dark design system (theme/tokens, mono-numeric type, app shell); restructured to a dashboard-first IA — bottom nav Inicio · Mapa · Sesiones · Mis puntos, profile via the avatar. Dashboard greeting + **real** nearby points (geolocation + `/api/points?bbox`); Sessions / My-points / stats / next-reservation are badged placeholder UI behind `*.mock.ts` (see [features.md](features.md)). **Merged + pushed to `main`** with the backend pricing/`simulate` commits; both feature branches deleted. Deployment approach recorded in [infra-0001](decisions/infra-0001-deployment.md); phases renumbered (PLAN revision 2026-06-28).
- **Prior — pre-charge simulation (Slice 4).** `app/services/simulation.py` + `POST /api/simulate`: power = min(vehicle, connector), AC flat / DC taper above 80% SoC → energy, duration, cost (reuses the pricing service). UI is a "Simular carga" dialog on the point-detail page (`frontend/src/simulate/`). Model write-up: [thesis/simulacion-de-recarga.md](thesis/simulacion-de-recarga.md). 104 backend tests, frontend lint/build/vitest green. (Now on `main`.)
- **Prior — pricing/estimate service.** `app/services/pricing.py`: real REVE tariff else `PVPC(hour) + margin[AC 0.22 / DC 0.32]`. Ingest nulls implausible tariffs (`> 2 €/kWh`); live-DB garbage rows nulled.
- **Data:** REVE seed complete (seed-once, serve-from-DB); tariff refresh + PVPC both on daily cron.

## Now (immediate)

- [ ] **Deploy securely (Phase 6 — priority)** — provision the host (Hetzner CX22, or Oracle Always-Free for €0), Caddy auto-HTTPS, same-origin; run the pre-deploy security gate and move the refresh crons to the server. Goal: a phone-accessible HTTPS URL. Approach + alternatives: [infra-0001](decisions/infra-0001-deployment.md).
- [ ] **CI/CD + releases** — GitHub Actions deploy-on-merge-to-`main`; branch protection (PR + green checks); begin semver tagging (`vX.Y.Z`); build toward **v1.0.0** = the evaluated version.
- [ ] **Default availability to "available"** (small backend change) — `aggregate_status` returns "available" instead of "unknown" when no `Evse.status`, so points show free until artificial demo data / a real source lands. Honesty note already in PLAN Data strategy.
- [ ] **Map viewport loading** (Phase 6 slice) — open-on-position + zoom-gated `bbox` fetch + padded cache; needs a small backend `bbox` on `GET /api/points/map`. Design in [features.md](features.md).
- [ ] **B2 lifecycle rule** (ops) — in the Backblaze UI on `tfm-db-backups`: keep-last-version + delete-older-than-N-days. (Optional: rotate the B2 app key.)

**Deferred:** `/api/recommend` (the PVPC optimiser + algorithm write-up) is folded into **Phase 7** — it targets an *owned* point's schedule, so it attaches once private points exist.

## Remaining (project arc)

- **Phase 7** — private points, bookings, sessions + simulated wallet/ledger + the `/api/recommend` optimiser.
- **Phase 8** — AI/agent assistant (planned; specific features to be decided).
- **Phase 9** — polish, security review + optimisation + scaling/cost strategy.
- **Phase 10** — thesis writing, incl. business-plan, deployment and roadmap chapters ([thesis/indice.md](thesis/indice.md)).

Carry-forward invariants (price cascade, refresh watermark gotcha) live in [PLAN.md](PLAN.md) and [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md) / [thesis/planificacion-de-siembra.md](thesis/planificacion-de-siembra.md).

## Commands

```bash
docker compose exec backend uv run python -m scripts.refresh_reve --status   # refresh cursor state
docker compose exec backend uv run pytest -q                                 # backend tests
docker compose exec frontend sh -c "pnpm run lint && pnpm run build"         # frontend lint + build
```
