# Next steps — where to start

_Working handoff: just enough to resume after time away. Keep it small. When a "Now" item lands, delete it, update **State**, and pull the next item up._

## State (2026-07-08)

- **Phases:** 1–2 done · 3 dropped · 4 done · 5 done (redesign + dashboard IA) · **6 in progress (deployment)** · 7 features+optimiser · 8 AI · 9 polish/security/scaling · 10 thesis. Detail: [PLAN.md](PLAN.md); history: git log.
- **Where things stand:** the repo side of Phase 6 is **built, verified, and merged to `main`** (2026-07-08) — prod compose stack (Caddy TLS, Postgres unpublished, supercronic scheduler replacing the host refresh crons), CI-gated CD workflow, env-driven CORS, root justfile, provisioning runbook. Decision trail: [infra-0001](decisions/infra-0001-deployment.md).
- **Nothing is deployed yet.** The app runs locally (dev stack via `just up`); the refresh/PVPC/backup crons still run from the laptop's crontab until the VPS exists. The CD workflow is **disabled** in the Actions tab (no server to deploy to) — re-enabling it is part of step 1 below.

## Now (in order)

1. [ ] **Provision + deploy** — follow [setup/deployment.md](setup/deployment.md) top to bottom: Hetzner CX22, DNS, server-side `.env`s with **rotated** secrets, restore a fresh seed dump (`just backup-seed` — never re-seed, ~12 days), first `up -d --build`, OAuth/Resend on the prod origin, CD secrets + re-enable the CD workflow, branch protection. Budget an evening.
2. [ ] **Security gate** before sharing the URL — checklist in [infra-0001](decisions/infra-0001-deployment.md); run `/security-review`. Then retire the laptop crontab lines and flip infra-0001 to `accepted`.
3. [ ] **Start semver tagging** (`vX.Y.Z`) toward **v1.0.0** = the evaluated build.
4. [ ] **Default availability to "available"** (small backend change) — `aggregate_status` returns "available" instead of "unknown" when no `Evse.status`. Honesty note already in PLAN Data strategy.
5. [ ] **Map viewport loading** (Phase 6 slice) — open-on-position + zoom-gated `bbox` fetch + padded cache; needs a small backend `bbox` on `GET /api/points/map`. Design in [features.md](features.md).
6. [ ] **B2 lifecycle rule** (ops) — in the Backblaze UI on `tfm-db-backups`: keep-last-version + delete-older-than-N-days. (Optional: rotate the B2 app key.)

## Remaining (project arc)

- **Phase 7** — private points, bookings, sessions + simulated wallet/ledger + the `/api/recommend` optimiser.
- **Phase 8** — AI/agent assistant (planned; specific features to be decided).
- **Phase 9** — polish, security review + optimisation + scaling/cost strategy.
- **Phase 10** — thesis writing, incl. business-plan, deployment and roadmap chapters ([thesis/indice.md](thesis/indice.md)).

Carry-forward invariants (price cascade, refresh watermark gotcha) live in [PLAN.md](PLAN.md) and [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md) / [thesis/planificacion-de-siembra.md](thesis/planificacion-de-siembra.md).

## Commands

`just --list` (task runner: `uv tool install rust-just` once). Day-to-day: `just up` · `just ci` before pushing · `just prod-up`/`prod-down` for a local prod smoke test.
