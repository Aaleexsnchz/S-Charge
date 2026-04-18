# Docker Operations Guide

Always run commands from the project root (`/home/aaleexsnchz/tfm`).

## Rule of thumb

| What changed | Command |
| --- | --- |
| Source code only | Nothing (auto-reloaded) |
| `docker-compose.yml` env vars or `.env` file | `docker compose up -d --force-recreate <service>` |
| `package.json` / `pyproject.toml` / `Dockerfile` | `docker compose build <service> && docker compose up -d --force-recreate <service>` |

---

## Frontend (React + Vite)

**Install new dependencies:**

```bash
# 1. Install on host (updates pnpm-lock.yaml)
cd frontend && pnpm add <package>

# 2. Rebuild image + recreate container (fresh musl-compiled node_modules)
docker compose build frontend && docker compose up -d --force-recreate frontend
```

**Edit source files (`.tsx`, `.ts`, `.css`):** Nothing needed — bind mount + HMR handles it automatically.

**Change `vite.config.ts`:** Vite picks it up automatically via HMR.

---

## Backend (Python/FastAPI)

**Install new dependencies:**

```bash
# 1. Add to pyproject.toml and sync lockfile (on host)
cd backend && uv add <package>

# 2. Rebuild image + recreate container
docker compose build backend && docker compose up -d --force-recreate backend
```

**Edit source files (`.py`):** Nothing needed — `--reload` watches `/app/app` automatically.

---

## Environment variables

**Change any `environment:` value in `docker-compose.yml` or `.env`:**

```bash
docker compose up -d --force-recreate <service>
```

No rebuild needed — env vars are injected at container start, not at build time.

---

## Why `--force-recreate` matters (frontend)

The frontend container uses an anonymous Docker volume to hold `node_modules` compiled for Alpine Linux (musl). Without `--force-recreate`, Docker reuses the old container and its stale volume, which can cause native binding errors or a `ERR_PNPM_NO_IMPORTER_MANIFEST_FOUND` restart loop. Force-recreating ensures the volume is repopulated from the freshly built image.
