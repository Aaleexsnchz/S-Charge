# S-Charge

**A Progressive Web App for managing EV charging in Spain.** Charging today is fragmented across one application per operator: a driver needs several accounts to find a point, and private chargers sitting idle in garages are invisible to everyone.

S-Charge puts both in one app. The real network is mirrored from the public **REVE** API, and on top of it sits what REVE does not offer:

- **Private charging points** — register your own charger and offer it for paid use.
- **Bookings** — reserve a slot instead of driving to an occupied point.
- **Charge simulation** — time and cost for your car model at a given point.
- **Price-optimised schedules** — plan a charge against real hourly electricity prices.

Built mobile-first at a 360px reference width, because the user is standing next to a charging point holding a phone.

Developed as a Master's thesis in IoT by a single developer. Scope and roadmap: [docs/plan/plan.md](docs/plan/plan.md).

## Quick start

Needs [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io), and Docker with the Compose plugin (for Postgres). The task runner is optional but assumed below: `uv tool install rust-just`.

```bash
git clone https://github.com/Aaleexsnchz/S-Charge.git && cd S-Charge
cp .env.example .env    # one file for the whole project

just install     # uv sync + pnpm install + git hooks
just up          # start Postgres
just migrate     # apply migrations
just api         # backend  → http://localhost:8000
just web         # frontend → http://localhost:5173   (second terminal)
```

| Service | URL | Notes |
| --- | --- | --- |
| Frontend | <http://localhost:5173> | Vite dev server; proxies `/api/*` to the backend so the session cookie stays first-party |
| Backend | <http://localhost:8000> | FastAPI, `--reload` |
| API docs | <http://localhost:8000/docs> | OpenAPI / Swagger UI |
| Postgres | `localhost:5432` | the one containerised piece in dev |

**Only Postgres runs in Docker.** The backend and frontend run natively so the toolchain that gates commits and runs in CI is the same one that runs the app — and so reloads are instant. The full containerised stack is what production runs; `just prod-up` smoke-tests it locally. See [docs/operations.md](docs/operations.md).

## Commands

The ones used daily. `just --list` has the rest, with descriptions.

| Command | Does |
| --- | --- |
| `just up` / `just down` | start / stop Postgres |
| `just api` | backend with reload |
| `just web` | Vite dev server |
| `just migrate` | apply migrations |
| `just revision "msg"` | autogenerate a migration — always review the diff |
| `just ci` | the full CI gate in parallel: lint, typecheck, tests, build. Run before pushing |
| `just prod-up` / `just prod-down` | the production stack locally, for a deploy smoke test |
| `just backup-seed` | PII-safe database dump, also the production bootstrap artifact |

Optional integrations (the app runs without them):

- **Google sign-in** — [docs/setup/google-oauth.md](docs/setup/google-oauth.md)
- **Verification & password-reset email** — [docs/setup/email.md](docs/setup/email.md)

## Tech stack

**Backend** — Python 3.13, FastAPI, SQLAlchemy 2.0 (async via asyncpg), Alembic, Pydantic v2, `fastapi-users`. Managed with `uv`; linted by Ruff, type-checked by basedpyright, tested with pytest.

**Frontend** — React + Vite + TypeScript, MUI v9 + Emotion, React Router, TanStack Query, MapLibre GL JS, installable as a PWA. Managed with `pnpm`; linted and formatted by Biome, tested with Vitest.

**Database** — PostgreSQL 18 (with `citext` for case-insensitive email).

**Production** — the same Compose stack on one EU VPS behind Caddy (automatic HTTPS), deployed by GitHub Actions when a `v*` tag is pushed ([infra-0003](docs/decisions/infra-0003-deploy-on-tag.md)).

Every library and the reason it was chosen: [docs/tech-stack.md](docs/tech-stack.md).

## Repo layout

```text
S-Charge/
├── backend/             FastAPI + Postgres backend
├── frontend/            React + Vite PWA
├── docs/                all project docs — see docs/README.md for the index
├── scripts/             host-level ops (DB backup to Backblaze B2)
├── docker-compose.yml       dev Postgres
├── docker-compose.prod.yml  prod stack (Caddy TLS + prod images + scheduler)
├── Caddyfile            reverse-proxy config for the prod stack
├── justfile             task runner recipes — `just --list`
├── openapi.json         exported API contract — `just gen-api`, committed, CI-gated
├── lefthook.yml         git hooks: lint/format on commit, the CI gate on push
├── CONTRIBUTING.md      branch, commit and doc-update conventions
└── AGENTS.md            code conventions and documentation discipline
```

## Contributing

Every change reaches `main` through a pull request. `just install` puts the lefthook hooks in place: commits lint and format the staged files, and pushes run the full CI gate, so `just ci` is the same thing on demand. The commit-time secret scan needs [betterleaks](https://github.com/betterleaks/betterleaks) on `PATH` — it is best-effort locally and authoritative as a CI job over the full history. Branch naming, commit conventions and what to update before opening the PR: **[CONTRIBUTING.md](CONTRIBUTING.md)**. The code-level conventions — layout, testing, migrations, documentation discipline — are in [AGENTS.md](AGENTS.md).

**Agent skills.** `.claude/skills/` is gitignored, so on a fresh clone materialise them from [skills-lock.json](skills-lock.json), which pins each skill to its `source`, `skillPath` and a content hash: install with the skill manager that wrote the lockfile, or copy the upstream `skillPath` to `.claude/skills/<name>/SKILL.md` by hand. Which skills this project uses, and what for: [docs/thesis/skills.md](docs/thesis/skills.md) — add a row the first time you use a new one.

## Documentation

The categorized index is at **[docs/README.md](docs/README.md)**. Most-reached entries:

- [docs/plan/plan.md](docs/plan/plan.md) — scope, phases, acceptance criteria
- [docs/features/](docs/features/) — one document per feature, with implementation status
- [docs/operations.md](docs/operations.md) — deploying, backups and restores, Postgres upgrades
- [docs/decisions/](docs/decisions/) — architectural decision records
- [docs/setup/deployment.md](docs/setup/deployment.md) — production provisioning runbook

## License

Licensing to be determined before any public release.
