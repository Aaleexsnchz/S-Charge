# Next steps — where to start

_Working handoff: just enough to resume after time away. Keep it small. When a "Now" item lands, delete it, update **State**, and pull the next item up._

## State (2026-07-27)

- **Phases:** 1–2 done · 3 dropped · 4 done · 5 done (redesign + dashboard IA) · **6 in progress (deployment)** · 7 features+optimiser · 8 AI · 9 polish/security/scaling · 10 thesis. Detail: [PLAN.md](PLAN.md); history: git log.
- **Where things stand:** the repo side of Phase 6 shipped on 2026-07-08 (prod compose stack — Caddy TLS, Postgres unpublished, supercronic scheduler replacing the host refresh crons — plus the CI-gated CD workflow, env-driven CORS, root justfile, provisioning runbook). On 2026-07-27 the four open Phase 6 choices were closed (Hetzner, registered domain, prod images built in CI, manual release tagging) and the rest of the phase was planned out: [phases/phase-6.md](phases/phase-6.md). Decision trail: [infra-0001](decisions/infra-0001-deployment.md).
- **Nothing is deployed yet.** The app runs locally (dev stack via `just up`); the refresh/PVPC/backup crons still run from the laptop's crontab until the VPS exists. The CD workflow is **disabled** in the Actions tab (no server to deploy to) — re-enabling it is Slice G.
- **Still to build in the repo** before the deploy is complete (Slice D): version stamping, the CI prod-image build, CD hardening, `release.yml`. `main` is not yet PR-protected.

## Now (in order)

1. [ ] **Finish Phase 6** — the whole remaining deployment arc is planned slice by slice in [phases/phase-6.md](phases/phase-6.md), ordered by dependency. **Start at Slice B step 1** (create the Hetzner account — ID verification can take hours) and buy the domain, since both have external latency that gates everything else. Host commands: [setup/deployment.md](setup/deployment.md). Budget an evening plus a morning.
2. [ ] **Default availability to "available"** (small backend change) — `aggregate_status` returns "available" instead of "unknown" when no `Evse.status`. Honesty note already in PLAN Data strategy.
3. [ ] **Map viewport loading** — open-on-position + zoom-gated `bbox` fetch + padded cache; needs a small backend `bbox` on `GET /api/points/map`. Deferred out of Phase 6 (no deployment dependency). Design in [features.md](features.md).

## Remaining (project arc)

- **Phase 7** — private points, bookings, sessions + simulated wallet/ledger + the `/api/recommend` optimiser.
- **Phase 8** — AI/agent assistant (planned; specific features to be decided).
- **Phase 9** — polish, security review + optimisation + scaling/cost strategy.
- **Phase 10** — thesis writing, incl. business-plan, deployment and roadmap chapters ([thesis/indice.md](thesis/indice.md)).

Carry-forward invariants (price cascade, refresh watermark gotcha) live in [PLAN.md](PLAN.md) and [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md) / [thesis/planificacion-de-siembra.md](thesis/planificacion-de-siembra.md).

## Commands

`just --list` (task runner: `uv tool install rust-just` once). Day-to-day: `just up` · `just ci` before pushing · `just prod-up`/`prod-down` for a local prod smoke test.
