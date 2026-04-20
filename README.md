# TFM — EV Charging PWA

A master's thesis project (IoT): a Progressive Web App for managing EV charging points, combining real data from the **REVE API** (the Spanish public charging network) with historical sessions from **ACN-Data** (the Adaptive Charging Network research dataset), plus user-contributed private charging points with simulated occupation.

The academic contribution lives in phases 3–4 (data integration, session simulation, and charging-schedule optimisation). Authentication, infrastructure, and business-feature scaffolding are kept deliberately library-backed — see [docs/auth-decisions.md](docs/auth-decisions.md) and [docs/future-work.md](docs/future-work.md) for the explicit scope record.

## Status

| Phase | Status |
|---|---|
| 0 — Tooling setup | ✅ done |
| 1 — Foundation (auth, schema, core UI) | 🚧 slice 1 backend done; frontend pending |
| 2 — REVE + Map | ⏳ not started |
| 3 — ACN import + analytics | ⏳ not started |
| 4 — Simulation + algorithm | ⏳ not started |
| 5 — Private points + bookings | ⏳ not started |
| 6 — Polish + deployment | ⏳ not started |
| 7 — Thesis writing | ⏳ not started |

See [PLAN.md](PLAN.md) for the full phase breakdown and estimates.

## Quick start

```bash
# clone and prepare env
git clone <repo> tfm && cd tfm
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# start all services
docker compose up
```

Services:

- **Backend API** — <http://localhost:8000> (OpenAPI docs at `/docs`)
- **Frontend** — <http://localhost:5173>
- **Postgres** — exposed on `:5432` for host-side tools

See [DOCKER.md](DOCKER.md) for when to rebuild vs. recreate the containers after a change.

## Tech stack

**Backend.** FastAPI, SQLAlchemy 2.0 (async via asyncpg), Alembic, Pydantic v2, fastapi-users for authentication, pwdlib + argon2-cffi for password hashing. Package manager: `uv`. Lint/typecheck: `ruff` + `mypy`.

**Frontend.** React + Vite + TypeScript, MUI, React Router. Zustand for client state. PWA installability via `vite-plugin-pwa`.

**Database.** PostgreSQL 16 with the `citext` extension (case-insensitive email lookup).

**Deployment.** Single Hetzner VPS (CX22), Nginx + Let's Encrypt. Deliberately rejected: Kubernetes, Vercel, Supabase — all overkill for thesis scope.

## Monorepo layout

```text
tfm/
├── backend/         FastAPI + Postgres backend — see backend/CLAUDE.md
├── frontend/        React + Vite + MUI frontend — see frontend/CLAUDE.md
├── docs/            Decision records, slice plans, future-work catalogue
├── docker-compose.yml
├── PLAN.md          Project scope, phases, deliverables, estimates
├── CONTRIBUTING.md  Branch naming, commit conventions, workflow
└── DOCKER.md        When to rebuild / recreate / do nothing
```

## Key architectural decisions

- **Authentication: single JWT in an HttpOnly cookie** via `fastapi-users` — no dual-token dance, no refresh tokens. Full 12-section decision record in [docs/auth-decisions.md](docs/auth-decisions.md); deferred security hardening in [docs/future-work.md](docs/future-work.md).
- **Rate limiting: deferred to Nginx `limit_req`** at the reverse proxy, not in application code. See [auth-decisions §7](docs/auth-decisions.md).
- **Payments and real-time occupation: simulated.** The thesis contribution is simulation and algorithm work, not payment integration. See the *Mocked* section in [PLAN.md](PLAN.md).
- **Deployment: single VPS.** Nginx terminates TLS, reverse-proxies to `uvicorn`, serves the built PWA statically. See [PLAN.md](PLAN.md) phase 6.

## Documentation index

- **[PLAN.md](PLAN.md)** — phases, deliverables, estimates
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — branch naming, Conventional Commits format, workflow
- **[DOCKER.md](DOCKER.md)** — when to rebuild, recreate, or do nothing after a change
- **[docs/auth-decisions.md](docs/auth-decisions.md)** — security decision record (ADR-style, 12 sections)
- **[docs/phase-1.md](docs/phase-1.md)** — slice-by-slice auth task plan
- **[docs/future-work.md](docs/future-work.md)** — items deliberately out of thesis scope
- **[docs/screens.md](docs/screens.md)** — UI screen specifications
- **[backend/CLAUDE.md](backend/CLAUDE.md)** / **[frontend/CLAUDE.md](frontend/CLAUDE.md)** — package-specific conventions and file layouts

## License

Master's thesis project; licensing to be determined before any public release.
