# TFM project memory

Master's thesis (IoT): a PWA for managing EV charging. Solo developer project. See [README.md](README.md) for setup and orientation.

## Source of truth

Read before proposing architectural or scope changes:

- **[docs/PLAN.md](docs/PLAN.md)** — phases, acceptance criteria, estimates. Living doc.
- **[docs/decisions/](docs/decisions/)** — architectural decision records (ADRs). Append-only.
- **[docs/thesis/](docs/thesis/)** — concept-level chapters for the thesis writeup.
- **[docs/DOCKER.md](docs/DOCKER.md)** — when to rebuild vs. recreate after a change.

Don't restate what those files cover. Link to them instead.

## Quickstart

Stack runs as three containers via Docker Compose. From the repo root:

```bash
docker compose up -d                                       # db + backend + frontend
docker compose exec backend uv run alembic upgrade head    # apply migrations
```

| Service  | URL                            | Notes                  |
| -------- | ------------------------------ | ---------------------- |
| Frontend | <http://localhost:5173>        | Vite dev server        |
| Backend  | <http://localhost:8000>        | FastAPI                |
| API docs | <http://localhost:8000/docs>   | OpenAPI / Swagger UI   |
| Postgres | `localhost:5432`               | `postgres:17-alpine`   |

Hot reload is on for both backend (`.py`) and frontend (`.ts`/`.tsx`) edits. See [docs/DOCKER.md](docs/DOCKER.md) for when a rebuild vs. recreate is needed.

## Working style

- **Responsive UI.** Mobile-first, 360px reference width.

## Git workflow

- `main` stays stable. Direct commits to `main` are fine for small low-risk changes (docs typos, single-line fixes). Use a branch for features, multi-file fixes, refactors, dependency upgrades, or anything that could break behaviour.
- **Branch naming**: `<type>/<scope>-<short-description>`, e.g. `feat/backend-user-profile`, `fix/frontend-navbar-overlap`.
- **Commit message format**: Conventional Commits — `<type>(<scope>): <imperative summary>`. One logical change per commit; no mixing unrelated changes.
- **Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`.
- **Scopes**: `backend`, `frontend`, `root`, `infra`.
- **Pre-commit hooks** ([.pre-commit-config.yaml](.pre-commit-config.yaml)) run backend `ruff check`, `ruff format --check`, `mypy`, and frontend `eslint` + `prettier`. Install with `pre-commit install` once per clone. No secrets or credentials in the diff.

## Backend

Python 3.12+, FastAPI, SQLAlchemy 2.0 (async via asyncpg), Alembic, Pydantic v2 + pydantic-settings, Uvicorn, pytest. Package manager: **uv**.

### Layout

```text
backend/
├── app/
│   ├── main.py          FastAPI app factory + router includes
│   ├── config.py        Settings (pydantic-settings, loads backend/.env)
│   ├── database.py      async engine + session factory
│   ├── models/          SQLAlchemy ORM models (one file per aggregate)
│   ├── schemas/         Pydantic request/response models
│   ├── routers/         FastAPI APIRouters (thin — delegate to services)
│   ├── services/        business logic (pure, testable, no FastAPI imports)
│   └── utils/           auth, timezone helpers, etc.
├── alembic/             migrations
├── scripts/             one-off ETL, seed, data generators
└── tests/               pytest (mirrors app/ structure)
```

Routers should be thin: parse input, call a service, return. Business logic lives in `services/`, never in route handlers.

### Alembic

- **Always autogenerate then review** — never trust the diff blindly.
- Run inside the backend container: `docker compose exec backend uv run alembic upgrade head`.
- Never edit applied migrations; add a new one.

### Testing

- `backend/tests/` mirrors `app/` structure.
- Service tests are unit tests (no DB). Route tests use a transactional fixture or a separate test DB.

### Lint and typecheck

Both must pass before commit:

```bash
uv run ruff check app tests            # E F I UP B, line length 100
uv run ruff format --check app tests
uv run mypy app tests
```

### Commands

```bash
uv sync --locked --all-groups                                                    # install deps
docker compose exec backend uv run alembic revision --autogenerate -m "msg"
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run pytest
```

In Docker (default): `.py` edits auto-reload; `pyproject.toml` changes need a rebuild. See [docs/DOCKER.md](docs/DOCKER.md).

## Frontend

React + Vite + TypeScript + MUI v7 (Emotion), in [frontend/](frontend/). Package manager: **pnpm**.

The Phase 1 scaffold ships the auth pages and PWA manifest. Per-icon imports from `@mui/icons-material` (never the barrel — breaks tree-shaking). Frontend ADRs go under `fe-NNNN` in [docs/decisions/](docs/decisions/) at the point of each decision.

## Documentation discipline

When a slice ships (or an edit would otherwise leave a doc stale), update these in the same commit as the code change:

- **[README.md](README.md)** — status table, any new major component, changed quick-start
- **[docs/PLAN.md](docs/PLAN.md)** — tick off acceptance bullets, adjust estimates, rewrite phase prose if shipped reality diverges from the plan (PLAN.md is living, not write-once)
- **[docs/thesis/](docs/thesis/)** — update the matching chapter when a cross-cutting system lands (auth, ETL, simulation)

Append-only docs (don't edit in place — add a dated revisions block at the top instead):

- **[docs/decisions/](docs/decisions/)** — one file per ADR
- **[docs/phases/phase-N.md](docs/phases/)** — frozen once the phase ships; differences from the spec go in the final commit message, not by rewriting history
