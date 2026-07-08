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

Both Dockerfiles are multi-stage:

- **`dev`** — what the dev Compose builds (`target: dev` in [docker-compose.yml](../docker-compose.yml)). Full dependencies incl. test/lint tooling, source bind-mounted, hot reload. Everything else in this guide assumes the `dev` target unless it says otherwise.
- **`prod`** — lean deployment image, built by [docker-compose.prod.yml](../docker-compose.prod.yml):
  - **Backend** — runtime deps only (`--no-dev`), non-root `appuser`, no `uv` at runtime, `HEALTHCHECK` on `/api/health`. ~330 MB vs ~860 MB for `dev`.
  - **Frontend** — built `dist/` served by nginx ([frontend/nginx.conf](../frontend/nginx.conf)) with SPA fallback for React Router. ~80 MB vs ~1.1 GB for `dev`. Serves static assets only — Caddy does the API routing in prod.
- **`scheduler`** (backend only) — `prod` plus [supercronic](https://github.com/aptible/supercronic) and [backend/crontab](../backend/crontab); runs the REVE/PVPC refresh ETLs in prod (no host cron, per [infra-0001](decisions/infra-0001-deployment.md) rev. 2026-06-30).

---

## Production stack

[docker-compose.prod.yml](../docker-compose.prod.yml) is **standalone** (own project name `ev-charging-app-prod`, not an override): Caddy terminates TLS on 80/443 ([Caddyfile](../Caddyfile), `SITE_ADDRESS` from the root `.env`) and proxies `/api/*` to the backend and everything else to nginx; Postgres has **no published port**. Provisioning: [setup/deployment.md](setup/deployment.md).

```bash
docker compose -f docker-compose.prod.yml up -d --build        # deploy / redeploy
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
docker compose -f docker-compose.prod.yml logs -f scheduler    # ETL job output
```

Every CD deploy rebuilds all images (cheap when nothing changed — cache hits), so the dev-side rebuild-vs-recreate distinctions above don't apply. ETL logs ride the container log stream; no `~/.reve-seed.log`-style host files. The stack can be smoke-tested locally next to the dev stack with `SITE_ADDRESS=localhost` in a root `.env` (self-signed cert warning is expected).

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

---

## Database backups

The seed costs ~12 days under REVE's 5 req/hr cap, so the populated DB is worth
protecting. [scripts/backup_db.sh](../scripts/backup_db.sh) writes a compressed
`pg_dump -Fc` archive to `backups/` (gitignored):

```bash
./scripts/backup_db.sh          # full dump (schema + all data) — disaster recovery
./scripts/backup_db.sh --seed   # excludes users/oauth_account rows — safe to publish
```

The `--seed` variant doubles as the production-bootstrap artifact (skips the
re-seed). Restore into a fresh, empty DB:

```bash
docker compose exec -T db pg_restore -U ev_charging_app -d ev_charging \
  --clean --if-exists --no-owner < backups/<file>.dump
```

### Offsite + automation

The offsite copy is **Backblaze B2** (bucket `tfm-db-backups`, server-side
encryption at rest), uploaded with `rclone`. Only the PII-safe seed dump goes
offsite — no `users`/`oauth_account` data ever leaves the machine.

[scripts/backup_db_cron.sh](../scripts/backup_db_cron.sh) runs weekly via cron
(Mondays 09:00 Madrid, logged to `~/.db-backup.log`): it writes a timestamped
seed dump to `backups/`, `rclone copy`s it to B2, and prunes both local and
offsite dumps beyond the most recent 8. It pins `rclone` and its config by
absolute path because cron uses a minimal `PATH` and does not load the profile.

The `rclone` B2 remote is named `b2`; credentials live in
`~/.config/rclone/rclone.conf` (chmod `600`, outside the repo). Restore from
offsite:

```bash
rclone copy b2:tfm-db-backups/<file>.dump /tmp/
docker compose exec -T db pg_restore -U ev_charging_app -d ev_charging \
  --clean --if-exists --no-owner < /tmp/<file>.dump
```

Offsite retention is also worth enforcing with a **B2 lifecycle rule** on the
bucket (keep only the last version / delete after N days) so hidden versions
from prunes don't accumulate.
