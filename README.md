# TFM — EV Charging PWA

A master's thesis project (IoT): a Progressive Web App for managing EV charging points. Combines real data from the **REVE API** (the Spanish public charging network) with historical sessions from **ACN-Data** (the Adaptive Charging Network research dataset, used internally for modelling), plus user-contributed private charging points with simulated occupation.

## Status

| Phase | Status |
| --- | --- |
| 1 — Foundation | `[x]` done |
| 2 — REVE seed + Map | `[~]` shipped + QA'd on real devices; seed cron mid-run (tariffs); post-seed incremental refresh ready |
| 3 — ACN import (internal) | `[~]` ingest backend shipped; real import + analysis notebook need `ACN_API_TOKEN` |
| 4 — Simulation + Algorithm | `[~]` slices 1–2 shipped (vehicle catalogue + PVPC ingest); 3–5 pending |
| 5 — Private points, Bookings + Sessions | `[ ]` not started |
| 6 — Polish + Deployment | `[ ]` not started |
| 7 — Thesis writing | `[ ]` not started |

See [docs/PLAN.md](docs/PLAN.md) for phase descriptions, acceptance criteria, and estimates.

## Quick start

```bash
git clone <repo> tfm && cd tfm
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

docker compose up -d
docker compose exec backend uv run alembic upgrade head    # apply migrations
```

Services:

- **Backend API** — <http://localhost:8000> (OpenAPI docs at `/docs`)
- **Frontend** — <http://localhost:5173> (Vite proxies `/api/*` to the backend so the session cookie stays first-party)
- **Postgres** — exposed on `:5432` for host-side tools

Hot reload is on for both backend (`.py`) and frontend (`.ts`/`.tsx`) edits. See [docs/DOCKER.md](docs/DOCKER.md) for when a rebuild vs. recreate is needed.

Optional integrations (the app runs without them):

- **Google sign-in** — [docs/setup/google-oauth.md](docs/setup/google-oauth.md)
- **Verification & password-reset email** — [docs/setup/email.md](docs/setup/email.md)

## Tech stack

**Backend** — Python 3.12+, FastAPI, SQLAlchemy 2.0 (async via asyncpg), Alembic, Pydantic v2, `fastapi-users` for authentication. Package manager: `uv`. Lint/format/typecheck: `ruff` + `basedpyright`.

**Frontend** — React + Vite + TypeScript + MUI v7 (Emotion), in `frontend/`. Package manager: `pnpm`. Lint/format: [Biome](https://biomejs.dev).

**Database** — PostgreSQL 17 with the `citext` extension (case-insensitive email lookup).

## Repo layout

```text
tfm/
├── backend/             FastAPI + Postgres backend
├── frontend/            React + Vite + MUI v7 PWA
├── docs/                all project docs — see docs/README.md for the index
├── docker-compose.yml
├── README.md
└── CLAUDE.md            project memory for Claude Code (also covers git workflow)
```

## Documentation

The full, categorized index lives at **[docs/README.md](docs/README.md)**. Start there. Most-reached entries:

- [docs/PLAN.md](docs/PLAN.md) — phases, acceptance criteria, estimates
- [docs/DOCKER.md](docs/DOCKER.md) — when to rebuild, recreate, or do nothing
- [docs/decisions/](docs/decisions/) — architectural decision records (ADRs)
- [docs/thesis/](docs/thesis/) — concept-level chapters for the thesis writeup

## License

Master's thesis project; licensing to be determined before any public release.
