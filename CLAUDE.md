# TFM — EV Charging PWA

Master's thesis (IoT): a PWA for managing EV charging points. Combines the **REVE API** (real Spanish charging network) with **ACN-Data** (real historical sessions) and supports user-contributed private charging points. Solo developer project.

## Source of Truth

- **[PLAN.md](PLAN.md)** — project scope, phases, deliverables, and timeline. Read this before proposing architectural or scope changes.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — branch naming, Conventional Commits format, workflow.
- **[DOCKER.md](DOCKER.md)** — when to rebuild, recreate, or do nothing after a change.

Do not restate what those files already cover. Link to them instead.

## Monorepo Layout

```text
tfm/
├── backend/      FastAPI + PostgreSQL + SQLAlchemy + Alembic  (see backend/CLAUDE.md)
├── frontend/     React + Vite + TypeScript + MUI              (see frontend/CLAUDE.md)
├── docker-compose.yml
└── PLAN.md
```

Each package has its own `CLAUDE.md` with stack-specific conventions. Work on changes inside the relevant package; don't reach across unless the task genuinely spans both.

## Entry Point

```bash
docker compose up
```

Starts Postgres, backend (FastAPI at `:8000`), and frontend (Vite at `:5173`). See `DOCKER.md` for when to rebuild vs. recreate.

## Commit Conventions

Conventional Commits, scoped to `backend`, `frontend`, `root`, or `infra`. One logical change per commit. Full rules in `CONTRIBUTING.md`.

## Deployment Target

Single Hetzner VPS (CX22) with Nginx + Let's Encrypt. **No Kubernetes, no Vercel, no Supabase** — deliberately rejected as overkill for thesis scope.

## What Is Mocked

Payments, commission payouts, and real-time occupation for private points are simulated. This is an intentional thesis decision documented in `PLAN.md` — do not try to build real payment integration.

## Working Style

- Solo developer, Python + React proficient. Skip beginner explanations.
- Prefer small focused commits over large batches.
- Plan before building: agree on approach before writing code for non-trivial work.
- Responsive UI is mandatory (mobile-first, tested on real iPhone + Android). PWA installability is a hard requirement.

## Documentation discipline

At the end of each slice (or when an edit would otherwise leave a doc stale), update these in the same commit as the code change:

- **[README.md](README.md)** — status table, any new major component, changed quick-start
- **[PLAN.md](PLAN.md)** — tick off completed checkboxes; adjust estimates if they shifted materially
- **[docs/future-work.md](docs/future-work.md)** — add newly-deferred items; remove ones we actually built
- **[backend/CLAUDE.md](backend/CLAUDE.md)** / **[frontend/CLAUDE.md](frontend/CLAUDE.md)** — update the file map or "architecture" section when a cross-cutting system lands (auth, ETL, simulation)

Write-once docs (don't touch unless a decision genuinely changes):

- **[docs/auth-decisions.md](docs/auth-decisions.md)** and future ADR-style docs — append new decisions with a date rather than editing in place (see the doc's own preamble)
- **[docs/phase-N.md](docs/)** — the slice spec is frozen once the slice ships; differences from the spec should be noted in the final commit message, not by rewriting history
