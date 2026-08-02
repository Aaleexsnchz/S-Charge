# Operations

Running, deploying and recovering the system. Day-to-day development commands are in the root [README](../README.md) and the [justfile](../justfile); one-time server provisioning is [setup/deployment.md](setup/deployment.md). This document is what you need *after* the thing exists.

Run every command from the project root.

Docker has two jobs here, and they are separate:

- **In dev it runs Postgres, nothing else.** The backend and frontend run natively (`just api`, `just web`), so the toolchain that gates commits and runs in CI is the same one that runs the app. The root `.env` therefore points `DATABASE_URL` at `@localhost:5432`, and Alembic, pytest and `python -m scripts.X` all run on the host.
- **In production it runs everything** — the stack in [docker-compose.prod.yml](../docker-compose.prod.yml), built from this repo and deployed by CI.

## Production stack

[docker-compose.prod.yml](../docker-compose.prod.yml) is **standalone** (own project name `ev-charging-app-prod`, not an override): Caddy terminates TLS on 80/443 ([Caddyfile](../Caddyfile), `SITE_ADDRESS` from the root `.env`) and proxies `/api/*` to the backend and everything else to nginx; Postgres has **no published port**.

```bash
docker compose -f docker-compose.prod.yml up -d --build        # deploy / redeploy
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
docker compose -f docker-compose.prod.yml logs -f scheduler    # ETL job output
```

Locally, `just prod-up` runs the same stack with `SITE_ADDRESS=localhost` (self-signed cert warning expected) — the way to smoke-test a deploy before pushing. Every CD deploy rebuilds all images, which is cheap when nothing changed because the layer cache hits.

Environment variables are read **at container creation**: after editing a server-side `.env`, use `up -d --force-recreate <service>`, never `restart`, or the container keeps the old values.

### Reaching the production database

Postgres has no published port, and that is the only thing keeping it off the internet — **not** the firewall. `ufw` does not filter Docker-published ports: Docker inserts its DNAT rules ahead of ufw's chain, so adding a `ports:` entry exposes the database publicly while `ufw status` still shows a correct-looking policy. Never add one to inspect production.

Tunnel over SSH instead — it publishes nothing and the port exists only on your machine, for the life of the connection:

```bash
ssh -L 5432:localhost:5432 deploy@s-charge.app
```

Leave that session open and point any client (DBeaver, `psql`) at `localhost:5432` on your laptop. Credentials are the server-side `.env`. If the dev stack is already using 5432 locally, map a different local port instead — `-L 55432:localhost:5432` — and connect to `localhost:55432`.

### Image stages

Both Dockerfiles are multi-stage, and every stage is a production stage — the dev stages were removed when development moved to the host:

- **Backend `prod`** — runtime deps only (`--no-dev`), non-root `appuser`, no `uv` at runtime, `HEALTHCHECK` on `/api/health`. ~330 MB.
- **Backend `scheduler`** — `prod` plus [supercronic](https://github.com/aptible/supercronic) and [backend/crontab](../backend/crontab); runs the REVE/PVPC refresh ETLs in production, so there is no host crontab to provision ([infra-0001](decisions/infra-0001-deployment.md)). ETL logs ride the container log stream.
- **Frontend `prod`** — built `dist/` served by nginx ([frontend/nginx.conf](../frontend/nginx.conf)) with SPA fallback for client-side routing. ~80 MB. Static assets only; Caddy does the API routing.

CI builds all three, so a broken Dockerfile fails there rather than on the server at deploy time.

> If a frontend package runs an install/build script (native deps like `sharp`), pnpm 11 blocks it by default. Approve it in [frontend/pnpm-workspace.yaml](../frontend/pnpm-workspace.yaml) under `allowBuilds` — otherwise the prod image build fails with `ERR_PNPM_IGNORED_BUILDS`.

## Major Postgres upgrades

Dev is on **17** while CI and production are on **18** — a deliberate, temporary split, because cutting the dev volume over is a manual step planned in [phases/phase-5.md](phases/phase-5.md).

**A major version bump is not a tag change.** The data directory format changes between majors, so a PG17 volume under an `18-alpine` image refuses to start with `database files are incompatible with server`. The local database holds the REVE seed, which costs ~12 days to rebuild, so dump before touching anything:

```bash
./scripts/backup_db.sh                  # full dump, taken with the OLD image still running
docker compose down -v                  # drops the old-major volume
docker compose up -d                    # fresh volume, new major
cd backend && uv run alembic upgrade head
docker compose exec -T db pg_restore -U ev_charging_app -d ev_charging \
  --clean --if-exists --no-owner < backups/<file>.dump
```

Rehearsed on 2026-08-01 into a throwaway 18.4 container: restore clean, row counts identical, `alembic current` at head, tests green. Expect one cosmetic difference — PG18 catalogues NOT NULL constraints as `pg_constraint` rows, so constraint counts jump (26 → 98 here) without anything actually changing.

`pg_upgrade` is the faster in-place alternative and PG18 keeps planner statistics across it, but it needs both majors' binaries in one image — not worth it at this size. **Production never performs a major upgrade**: it is provisioned fresh and restores a seed dump into an empty cluster.

## Database backups

The seed costs ~12 days under REVE's 5 req/hr cap, so the populated database is worth protecting. [scripts/backup_db.sh](../scripts/backup_db.sh) writes a compressed `pg_dump -Fc` archive to `backups/` (gitignored):

```bash
./scripts/backup_db.sh          # full dump (schema + all data) — disaster recovery
./scripts/backup_db.sh --seed   # excludes users/oauth_account rows — safe to publish
```

The `--seed` variant doubles as the production-bootstrap artifact (it skips the re-seed). Restore into a fresh, empty database:

```bash
docker compose exec -T db pg_restore -U ev_charging_app -d ev_charging \
  --clean --if-exists --no-owner < backups/<file>.dump
```

> **Check the dump is not empty.** The weekly cron produced a 0-byte file on 2026-07-13 and nothing noticed, because the script has no size check. A backup you have not restored — or at least sized — is not a backup.

### Offsite + automation

The offsite copy is **Backblaze B2** (bucket `tfm-db-backups`, server-side encryption at rest), uploaded with `rclone`. Only the PII-safe seed dump goes offsite — no `users`/`oauth_account` data ever leaves the machine.

[scripts/backup_db_cron.sh](../scripts/backup_db_cron.sh) runs weekly via cron (Mondays 09:00 Madrid, logged to `~/.db-backup.log`): it writes a timestamped seed dump to `backups/`, `rclone copy`s it to B2, and prunes both local and offsite dumps beyond the most recent 8. It pins `rclone` and its config by absolute path because cron uses a minimal `PATH` and does not load the profile.

The `rclone` B2 remote is named `b2`; credentials live in `~/.config/rclone/rclone.conf` (chmod `600`, outside the repo). Restore from offsite:

```bash
rclone copy b2:tfm-db-backups/<file>.dump /tmp/
docker compose exec -T db pg_restore -U ev_charging_app -d ev_charging \
  --clean --if-exists --no-owner < /tmp/<file>.dump
```

Offsite retention is also worth enforcing with a **B2 lifecycle rule** on the bucket (keep only the last version / delete after N days) so hidden versions from prunes don't accumulate.
