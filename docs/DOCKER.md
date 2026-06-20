# Docker Operations Guide

Always run commands from the project root (`/home/aaleexsnchz/tfm`).

## Rule of thumb

| What changed | Command |
| --- | --- |
| Source code only | Nothing (auto-reloaded) |
| `docker-compose.yml` env vars or `.env` file | `docker compose up -d --force-recreate <service>` |
| `package.json` / `pyproject.toml` / `Dockerfile` | `docker compose build <service> && docker compose up -d --force-recreate -V <service>` |

---

## Multi-stage builds: `dev` vs `prod`

Both Dockerfiles are multi-stage with two final targets:

- **`dev`** — what Compose builds (`target: dev` in [docker-compose.yml](../docker-compose.yml)). Full dependencies incl. test/lint tooling, source bind-mounted, hot reload. Everything else in this guide assumes the `dev` target.
- **`prod`** — lean deployment image, built explicitly (Compose never builds it):
  - **Backend** — runtime deps only (`--no-dev`), non-root `appuser`, no `uv` at runtime, `HEALTHCHECK` on `/api/health`. ~330 MB vs ~860 MB for `dev`.
  - **Frontend** — built `dist/` served by nginx ([frontend/nginx.conf](../frontend/nginx.conf)) with SPA fallback for React Router. ~80 MB vs ~1.1 GB for `dev`. Serves static assets only — API proxying is deployment-specific.

Build the prod images directly (outside Compose):

```bash
docker build --target prod -t tfm-backend ./backend
docker build --target prod -t tfm-frontend ./frontend
```

---

## Frontend (React + Vite)

**Install new dependencies:**

```bash
# 1. Install on host (updates pnpm-lock.yaml)
cd frontend && pnpm add <package>

# 2. Rebuild image + recreate container (fresh musl-compiled node_modules)
docker compose build frontend && docker compose up -d --force-recreate -V frontend
```

> If the new package runs an install/build script (native deps like `sharp`), pnpm 11 blocks it by default. Approve it in [frontend/pnpm-workspace.yaml](../frontend/pnpm-workspace.yaml) under `allowBuilds` (`<pkg>: true`, or `false` to keep it skipped) — otherwise the image build fails with `ERR_PNPM_IGNORED_BUILDS`.

**Edit source files (`.tsx`, `.ts`, `.css`):** Nothing needed — bind mount + HMR handles it automatically.

**Change `vite.config.ts`:** Vite picks it up automatically via HMR.

---

## Backend (Python/FastAPI)

**Install new dependencies:**

```bash
# 1. Add to pyproject.toml and sync lockfile (on host)
cd backend && uv add <package>

# 2. Rebuild image + recreate container
docker compose build backend && docker compose up -d --force-recreate -V backend
```

**Edit source files (`.py`):** Nothing needed — `--reload` watches `/app/app` automatically.

**Database migrations (Alembic):** Run inside the backend container so the `db` hostname resolves:

```bash
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run alembic revision --autogenerate -m "msg"
```

Running `alembic` from the host fails with `Temporary failure in name resolution` because `DATABASE_URL` in `backend/.env` points to `@db:5432` (the Docker service name, not reachable from the host). To run from the host anyway, override the URL inline with `@localhost:5432`.

---

## Environment variables

**Change any `environment:` value in `docker-compose.yml` or `.env`:**

```bash
docker compose up -d --force-recreate <service>
```

No rebuild needed — env vars are injected at container start, not at build time.

---

## Why `--force-recreate -V` matters (frontend)

The frontend container uses an anonymous Docker volume to hold `node_modules` compiled for Alpine Linux (musl). On a dependency change you need both flags:

- `--force-recreate` discards the old container so the new image is used.
- `-V` (`--renew-anon-volumes`) discards the old anonymous `node_modules` volume so the freshly built image's `node_modules` becomes the source of truth.

Without `-V`, Docker Compose keeps the old anon volume across recreates, leaving the container with stale `node_modules` from the previous image. Symptoms include `Cannot find package '...' imported from /app/node_modules/...` errors at dev-server startup and `ERR_PNPM_NO_IMPORTER_MANIFEST_FOUND` restart loops.
