# TFM project memory

Master's thesis (IoT): a PWA for managing EV charging. Solo developer project. See [README.md](README.md) for setup and orientation.

## Source of truth

Read before proposing architectural or scope changes:

- **[docs/README.md](docs/README.md)** — documentation index; the map of every doc and where it lives. Start here to locate anything.
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

Common commands are wrapped as recipes in the root [justfile](justfile) — `just --list` shows them (`just ci` runs everything CI gates on). Install the runner once with `uv tool install rust-just`. The raw commands below still work; the justfile is a convenience for humans, and nothing in CI/CD depends on it.

## Working style

- **Responsive UI.** Mobile-first, 360px reference width.

## Git workflow

- **GitHub Flow: every change reaches `main` through a pull request.** Branch off `main`, push, open a PR, merge once CI is green. `main` is protected — no direct commits, no force-pushes — and it is what production runs, so it must stay deployable at all times.
- **Branch naming**: `<type>/<scope>-<short-description>`, e.g. `feat/backend-user-profile`, `fix/frontend-navbar-overlap`.
- **Commit message format**: Conventional Commits — `<type>(<scope>): <imperative summary>`. One logical change per commit; no mixing unrelated changes.
- **Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`.
- **Scopes**: `backend`, `frontend`, `root`, `infra`.
- **Pre-commit hooks** ([.pre-commit-config.yaml](.pre-commit-config.yaml)) run `check-yaml`, `betterleaks` (secret scan), backend `ruff check` + `ruff format --check`, and frontend `biome` (lint + format). Install with `pre-commit install` once per clone. No secrets or credentials in the diff.
- **`basedpyright` and the test suites are NOT in pre-commit** — they gate only in CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)), which runs ruff + `basedpyright` + `pytest` (backend) and biome + `vitest` + `build` (frontend). Run `basedpyright` and the tests yourself before pushing, or CI will fail on a commit that committed cleanly — `just ci` runs the whole gate in one command.

## Releases

Semantic versioning, tagged **manually** — the version number is a deliberate statement about scope, never derived from commit types. Rationale and the rejected alternatives: [docs/phases/phase-6.md](docs/phases/phase-6.md).

- **Bump rules**: minor (`v0.7.0`) when a phase or a meaningful feature set ships; patch (`v0.7.1`) for fixes on top; `v0.1.0` was the first production deploy and **`v1.0.0` is the build presented for the thesis**.
- **Cutting a release** — from a green `main` that is already deployed:

  ```bash
  git checkout main && git pull
  git tag -a v0.7.0 -m "Phase 7: private points, bookings, wallet"
  git push --tags
  ```

  A tag push triggers the release workflow (`.github/workflows/release.yml` — lands with Phase 6 Slice D), which creates the GitHub Release with notes generated from the merged PR titles. Nothing else to update by hand.
- **The running version is derived from the tag.** `git describe --tags` feeds an `APP_VERSION` build arg at image build; it surfaces in `/api/health` and on the profile screen. Between tags it reads `v0.7.0-3-gabc1234`, so production always says how far ahead of the last release it is. Do **not** hand-edit version strings in `backend/pyproject.toml` or `frontend/package.json` — they are not the source of truth.

## Backend

Python 3.12+, FastAPI, SQLAlchemy 2.0 (async via asyncpg), Alembic, Pydantic v2 + pydantic-settings, Uvicorn, pytest. Package manager: **uv**.

### Layout

```text
backend/
├── app/
│   ├── main.py          FastAPI app factory + router includes
│   ├── config.py        Settings (pydantic-settings, loads backend/.env)
│   ├── database.py      async engine + session factory
│   ├── dependencies.py  FastAPI dependencies (get_db, get_user_db)
│   ├── models/          SQLAlchemy ORM models (one file per aggregate)
│   ├── schemas/         Pydantic request/response models
│   ├── routers/         FastAPI APIRouters (thin — delegate to services)
│   ├── services/        business logic (pure, testable, no FastAPI imports)
│   ├── integrations/    HTTP clients for external APIs (REVE)
│   ├── etl/             import/upsert logic + cursor helpers for seeds
│   └── utils/           auth, timezone helpers, etc.
├── alembic/             migrations
├── scripts/             one-off ETL, seed, data generators (Python, run in-container via `uv run python -m scripts.X`)
└── tests/               pytest (mirrors app/ structure)
```

Routers should be thin: parse input, call a service, return. Business logic lives in `services/`, never in route handlers.

Host-level ops tooling (bash, run on the host / from cron — e.g. DB backup) lives in the **repo-root `scripts/`**, separate from `backend/scripts/`; see [docs/DOCKER.md](docs/DOCKER.md).

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
uv run ruff check
uv run ruff format --check
uv run basedpyright
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

Per-icon imports from `@mui/icons-material` (never the barrel — breaks tree-shaking). Frontend ADRs go under `fe-NNNN` in [docs/decisions/](docs/decisions/) at the point of each decision.

### Layout

**Feature-first**: a file lives with the feature that owns it; `components/` and `lib/` hold only what is shared across features. Cross-folder imports use the `@/` alias (`@/* → src/*`, configured in [frontend/tsconfig.app.json](frontend/tsconfig.app.json) and [frontend/vite.config.ts](frontend/vite.config.ts)); same-folder imports stay relative (`./`).

```text
frontend/src/
├── app/          application shell: router (routes.tsx), root layout, error + not-found pages
├── features/     one folder per domain (auth, map, points, simulate, home, profile)
├── components/   shared UI reused across features (never feature-specific)
├── lib/          library wrappers + HTTP client (lib/api: openapi-fetch client + generated schema)
├── types/        shared cross-feature types
├── styles/       global CSS
├── assets/       static assets
├── main.tsx      entry: providers (theme, query, snackbar) + RouterProvider
└── theme.ts      MUI theme
```

Features stay **flat** until they grow; add a `components/`/`hooks/` subfolder inside a feature (or a top-level `hooks/`/`utils/`) only when the first file needs it — don't pre-create empty buckets. No per-feature barrel (`index.ts`) files: they work against tree-shaking (same reason as the icon rule above), so import modules directly.

### Lint and format

[Biome](https://biomejs.dev) handles both lint and format (config in [frontend/biome.json](frontend/biome.json)). Must pass before commit:

```bash
pnpm run lint            # biome check — lint + format check + import sort
pnpm run format          # biome check --write — auto-fix lint + format
```

### Commands

Run from [frontend/](frontend/):

```bash
pnpm install             # install deps
pnpm run dev             # Vite dev server (http://localhost:5173)
pnpm run build           # tsc -b && vite build — typecheck + production build
pnpm run test            # vitest
pnpm run gen:api         # regenerate API types from the backend OpenAPI schema
```

In Docker (default): `.ts`/`.tsx` edits hot-reload; `package.json`/lockfile changes need a rebuild. See [docs/DOCKER.md](docs/DOCKER.md).

## Documentation discipline

When a slice ships (or an edit would otherwise leave a doc stale), update these in the same commit as the code change:

- **[README.md](README.md)** — status table, any new major component, changed quick-start
- **[docs/README.md](docs/README.md)** — add or adjust the index row when you add, move, or remove a doc; it's the single source of truth for the doc list
- **[docs/PLAN.md](docs/PLAN.md)** — tick off acceptance bullets, adjust estimates, rewrite phase prose if shipped reality diverges from the plan (PLAN.md is living, not write-once)
- **[docs/thesis/](docs/thesis/)** — update the matching chapter when a cross-cutting system lands (auth, ETL, simulation); write a new chapter if none matches. **Chapters are written in Spanish** — the thesis is presented in Spanish, and these are its source material. Keep established technical terms in English (bearer token, upsert, rate limit) where a Spanish translation would be unusual in academic CS writing.

Append-only docs (don't edit in place — add a dated revisions block at the top instead):

- **[docs/decisions/](docs/decisions/)** — one file per ADR
- **[docs/phases/phase-N.md](docs/phases/)** — frozen once the phase ships; differences from the spec go in the final commit message, not by rewriting history
