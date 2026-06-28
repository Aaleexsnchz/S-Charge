# TFM — EV Charging PWA

A master's thesis project (IoT): a Progressive Web App for managing EV charging points. It unifies, under one app, what is today fragmented across each operator's own application, and improves on Spain's public **REVE** app (which only views points and plans routes). It seeds the real Spanish network from the **REVE API** and adds the functionality REVE lacks: user-contributed private charging points with paid use, bookings, price/time charging optimisation over real PVPC prices, charge simulation, and AI/agent features. The thesis pillar is the application itself, alongside a business plan, a deployment/scaling strategy, and a roadmap.

## Status

| Phase | Status |
| --- | --- |
| 1 — Foundation | `[x]` done |
| 2 — REVE seed + Map | `[x]` shipped + QA'd on real devices; seed complete; tariff refresh on cron |
| 3 — ACN import | `[-]` **dropped** (scope pivot 2026-06-21; ACN kept only as a documented road-not-taken) |
| 4 — Simulation + Algorithm | `[x]` done (vehicle catalogue, PVPC ingest, `/api/simulate` + UI); synthetic availability dropped, `/api/recommend` → Phase 7 |
| 5 — Frontend redesign + dashboard-first IA | `[x]` done (s-charge dark design system; 4-tab IA; real nearby points; placeholder UIs) |
| 6 — Deployment + CI/CD + releases | `[~]` in progress (secure phone-accessible instance, then releases toward v1.0.0) |
| 7 — Private points, Bookings, Sessions + Wallet + optimiser | `[ ]` not started |
| 8 — AI/agent assistant | `[ ]` planned; specific features to be decided |
| 9 — Polish, security review + optimisation + scaling strategy | `[ ]` not started |
| 10 — Thesis writing | `[ ]` not started |

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
