# Operations

Running, deploying and recovering the system. Day-to-day development commands are in the root [README](../README.md) and the [justfile](../justfile); one-time server provisioning is [setup/deployment.md](setup/deployment.md). This document is what you need *after* the thing exists.

Run every command from the project root.

Docker has two jobs here, and they are separate:

- **In dev it runs Postgres, nothing else.** The backend and frontend run natively (`just api`, `just web`), so the toolchain that gates commits and runs in CI is the same one that runs the app. The root `.env` therefore points `DATABASE_URL` at `@localhost:5432`, and Alembic, pytest and `python -m scripts.X` all run on the host.
- **In production it runs everything** — the stack in [docker-compose.prod.yml](../docker-compose.prod.yml), built from this repo and deployed by CI.

## Reaching the production host

```bash
ssh s-charge          # ~/.ssh/config alias -> deploy@s-charge.app, key id_ed25519_s-charge
cd /opt/s-charge      # the checkout cd.yml deploys into
```

The key is passphrase-protected, so a non-interactive `ssh -o BatchMode=yes` fails with *"Permission denied (publickey)"* even though the key is authorized — that is the prompt being suppressed, not a broken alias.

**Three different keys are in play, and confusing them wastes an afternoon:**

| Key | Authenticates | Passphrase |
| --- | --- | --- |
| `~/.ssh/id_ed25519_s-charge` | you → the host, interactively | yes |
| `~/.ssh/s-charge_deploy` (secret `DEPLOY_SSH_KEY`) | GitHub Actions → the host | no — CI cannot type one |
| repository deploy key, on the host | the host → GitHub, to `git fetch` | no |

## Production stack

[docker-compose.prod.yml](../docker-compose.prod.yml) is **standalone** (own project name `s-charge-prod`, not an override): Caddy terminates TLS on 80/443 ([Caddyfile](../Caddyfile), `SITE_ADDRESS` from the root `.env`) and proxies `/api/*` to the backend and everything else to nginx; Postgres has **no published port**.

**The volumes carry the project's name, and getting there needed a migration.** Compose derives a volume's real name from the project name, so renaming the project to `s-charge` would have pointed Postgres at a brand-new empty volume while the real one sat orphaned. They were pinned to their old names to prevent exactly that, which worked and then left every `up` warning about a mismatch it could not itself resolve. Both stacks have since been copied onto correctly-named volumes, so the pins are gone — see [Renaming a volume](#renaming-a-volume) if it is ever needed again.

```bash
docker compose -f docker-compose.prod.yml up -d --build        # deploy / redeploy
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
docker compose -f docker-compose.prod.yml logs -f scheduler    # ETL job output
```

**The `scheduler` service is ordinary — `up -d` starts, updates and stops it like any other.** It spent Phase 5 behind a Compose profile so that a deploy could not start an unattended REVE tick while the watermark was parked. Phase 6 turned the ETLs on permanently, and the profile promptly inverted from a guard into a hazard: a profiled service is *skipped* by `up -d` rather than recreated, so **every deploy left the scheduler running the previous image**, and `down` left it running entirely — a tear-down that looks complete while a cron keeps ticking against the database.

### Renaming a volume

Docker cannot relabel a volume in place, so a volume whose name no longer matches its project has to be copied into a new one. Done on both stacks on 2026-08-23; the source is left untouched throughout, so a failure costs nothing.

```bash
docker compose -f docker-compose.prod.yml down          # nothing may be writing

# Let Compose create the new volumes — never `docker volume create`, which makes
# a volume Compose does not recognise as its own and warns about ever after.
docker compose -f docker-compose.prod.yml up -d --no-deps db caddy
docker compose -f docker-compose.prod.yml down

for v in postgres_data caddy_data caddy_config; do
  docker run --rm -v ev-charging-app-prod_$v:/from:ro -v s-charge-prod_$v:/to \
    alpine sh -c 'find /to -mindepth 1 -delete && cd /from && cp -a . /to/'
  docker run --rm -v ev-charging-app-prod_$v:/from:ro -v s-charge-prod_$v:/to:ro \
    alpine sh -c 'diff -r /from /to && echo "$v IDENTICAL"'
done
```

**Verify by content, never by size.** `du -sb` reports a few KB of difference on a byte-identical copy — directory metadata — so an empty `diff -r` is the only real check. Only after all of them pass should the compose file drop its `name:` pins and the stack come back up.

**Do not reach for `external: true`** to silence a name mismatch: it makes the stack refuse to start anywhere the volume does not already exist, which is every new host and every `just prod-up`.

Locally, `just prod-up` runs the same stack with `SITE_ADDRESS=localhost` (self-signed cert warning expected) — the way to smoke-test a deploy before pushing. Every CD deploy rebuilds all images, which is cheap when nothing changed because the layer cache hits.

Environment variables are read **at container creation**: after editing a server-side `.env`, use `up -d --force-recreate <service>`, never `restart`, or the container keeps the old values.

### Reaching the production database

**Never publish Postgres on `0.0.0.0`.** `ufw` does not filter Docker-published ports: Docker inserts its DNAT rules ahead of ufw's chain, so a plain `ports: ["5432:5432"]` exposes the database to the internet while `ufw status` still shows a correct-looking policy.

`db` is therefore bound to **loopback only** — `127.0.0.1:5432:5432`. That rule matches a destination no packet from outside can carry, so the database is reachable from the host and from nothing else. It grants a local shell nothing it did not already have through `docker compose exec`.

### The dev database

`docker-compose.yml` binds it to `127.0.0.1:5432` too, for the same reason: a `0.0.0.0` bind accepts connections from anyone on the same wifi. Connect DBeaver straight to `localhost:5432` — no tunnel, credentials from the root `.env`.

**On WSL2, test this after changing it.** Windows reaches WSL services through a localhost relay, and whether it forwards to a service bound inside the distro to `127.0.0.1` rather than `0.0.0.0` depends on the WSL version and whether mirrored networking is on. If a Windows-side client stops connecting, that is why — run the client inside WSL, enable mirrored networking, or put the bind back.

### From a GUI client

Tunnel over SSH; the port exists only on your machine, for the life of the connection.

```bash
ssh -L 55432:localhost:5432 s-charge
```

Leave that session open and point DBeaver (or `psql`) at `localhost:55432`. Credentials are the server-side `.env` — rotated at first deploy, so not the dev ones. Port 55432 rather than 5432 because the dev stack holds 5432 locally.

**Use the `s-charge` alias, not `deploy@s-charge.app`.** The `Host s-charge` block in `~/.ssh/config` is what supplies the user and `IdentityFile`; spelling the hostname out matches no block, so ssh offers its default keys and the server answers `Permission denied (publickey)`.

### Ad-hoc SQL on the host

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT count(*) FROM charging_points;
SQL
```

**The single quotes are load-bearing.** `$POSTGRES_USER` and `$POSTGRES_DB` exist in the container, not in the host shell — double-quote them and they expand to nothing, psql falls back to the OS user, and the connection fails with `role "root" does not exist`. The same trap is why [backup_db.sh](../scripts/backup_db.sh) needs its credentials supplied from the crontab entry.

### Image stages

Both Dockerfiles are multi-stage, and every stage is a production stage — the dev stages were removed when development moved to the host:

- **Backend `prod`** — runtime deps only (`--no-dev`), non-root `appuser`, no `uv` at runtime, `HEALTHCHECK` on `/api/health`. ~330 MB.
- **Backend `scheduler`** — `prod` plus [supercronic](https://github.com/aptible/supercronic) and [backend/crontab](../backend/crontab); owns the REVE/PVPC refresh ETLs in production, so there is no host crontab to provision ([infra-0001](decisions/infra-0001-deployment.md)). ETL logs ride the container log stream. Gated behind its profile, as above, and not running yet. CI still builds it, via `docker build --target scheduler` rather than through Compose. ~356 MB.
- **Frontend `prod`** — built `dist/` served by nginx ([frontend/nginx.conf](../frontend/nginx.conf)) with SPA fallback for client-side routing. ~80 MB. Static assets only; Caddy does the API routing.

CI builds all three, so a broken Dockerfile fails there rather than on the server at deploy time.

> If a frontend package runs an install/build script (native deps like `sharp`), pnpm 11 blocks it by default. Approve it in [frontend/pnpm-workspace.yaml](../frontend/pnpm-workspace.yaml) under `allowBuilds` — otherwise the prod image build fails with `ERR_PNPM_IGNORED_BUILDS`.

## The REVE refresh

`refresh_reve` drains `/connectors/tariffs` on the hour under a 5 req/hour cap, and reports itself:

```bash
docker compose -f docker-compose.prod.yml exec -T backend python -m scripts.refresh_reve --status
```

That makes no REVE call, so it is free to run as often as you like. A healthy drain shows `next page` climbing by 5 an hour, `cycle end` **frozen** (it is the cycle's upper bound and must not move mid-flight), `watermark` unchanged until the cycle drains, and `failing since` empty. The first line is the catalogue backlog — connectors REVE serves tariffs for that the mirror does not hold; see [be-0003](decisions/be-0003-price-on-the-connector.md) and the [prices chapter](thesis/precios-y-actualizacion.md).

**`--restart-cycle` rewinds an in-flight cycle to page 1 without moving its window.** It exists because pages already drained are otherwise unreachable: the endpoint has no `date_to`, and a completed cycle advances the watermark past them permanently. Use it when a fix ships mid-drain and the pages that passed before it need re-reading — rewinding costs one page of budget per page re-read, and each recovers roughly 26 connectors that would otherwise wait ~243 days for their next repricing.

**Deploy first, rewind second.** Rewinding before the fix is live re-reads those pages with the old code and discards them again.

**Never run either ETL against production from a laptop.** The 5 req/hour cap is per API key, so a local run steals from the scheduler's budget and the two will fight over the same cursor — the advisory lock keeps them from corrupting it, but one of them simply loses its tick.

## Major Postgres upgrades

Dev, CI and production all run **18**. The dev volume was cut over in Phase 5 by the procedure below; keep it here because the next major will need it again.

**A major version bump is not a tag change.** The data directory format changes between majors, so a PG17 volume under an `18-alpine` image refuses to start with `database files are incompatible with server`. The local database holds the REVE seed, which costs ~12 days to rebuild, so dump before touching anything.

**Going to 18 also moves the mount point.** From 18 the images store data in a major-version subdirectory and declare `/var/lib/postgresql` as the volume, so `PGDATA` is `/var/lib/postgresql/18/docker`. A compose file still mounting the 17-era `/var/lib/postgresql/data` makes the entrypoint abort with *"there appears to be PostgreSQL data in /var/lib/postgresql/data (unused mount/volume)"* — deliberately, because the alternative is writing the cluster into the container's own layer, where the next `up --build` silently discards it. Change the mount in the same edit as the tag:

```yaml
volumes:
  - postgres_data:/var/lib/postgresql      # not /var/lib/postgresql/data
```

```bash
./scripts/backup_db.sh                  # full dump, taken with the OLD image still running
docker compose down -v                  # drops the old-major volume
# edit docker-compose.yml: image tag AND the mount path above
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

The script now refuses to leave a dump it does not believe in: it keeps `pg_dump`'s exit status, sizes the result, and deletes the file and exits non-zero if either looks wrong. Both halves are needed — the shell creates the file before `pg_dump` runs, so a crash leaves a plausible artifact behind, and a dump that exits `0` while writing nothing passes a status check. That is how a 0-byte file reached the offsite bucket on 2026-07-13 and was noticed by nobody. **Sizing is still not restoring**; the automated restore check is a Phase 13 item.

There is a second kind of dump on the server: **`backups/pre-migrate-*.dump`**, written by CD immediately before `alembic upgrade head` and pruned to the last five. They exist because a rollback returns the code but not the schema — restoring one is how you undo a migration. They are full dumps, they are not sent offsite, and they are not a substitute for the weekly backup.

### Offsite + automation

The offsite copy is **Backblaze B2** (bucket `S-Charge`, server-side encryption at rest, *keep only the last version* lifecycle rule), uploaded with `rclone`. Only the PII-safe seed dump goes offsite — no `users`/`oauth_account` data ever leaves the machine.

**The server authenticates with its own bucket-scoped key**, not the laptop's. It is internet-facing, so the blast radius worth accepting is one bucket of PII-safe dumps, and it can be revoked without disturbing anything else. A scoped key cannot `rclone lsd b2:` — listing all buckets is the permission deliberately withheld — so check it with `rclone lsf b2:S-Charge`.

**Cron must set `COMPOSE_FILE=docker-compose.prod.yml`.** Without it the dump addresses the dev project, which has never run on the server.

**This ran on the development laptop and, until 2026-08-23, on nothing else.** The server had no `rclone`, no config and no cron entry, so from the day it was provisioned there was no offsite copy of the seed at all — every copy lived on the one host, including the dumps meant to survive losing it. Nobody noticed because the only place it would have said so is a cron log that exists only once the cron does. Two things worth keeping: **a documented backup is not a backup**, and provisioning a host means moving its scheduled work too, not only its services.

[scripts/backup_db_cron.sh](../scripts/backup_db_cron.sh) runs weekly via cron (Mondays 09:00 Madrid, logged to `~/.db-backup.log`): it writes a timestamped seed dump to `backups/`, `rclone copy`s it to B2, and prunes both local and offsite dumps beyond the most recent 8. Cron uses a minimal `PATH` and does not load the profile, so the script sets both `PATH` and `RCLONE_CONFIG` itself, deriving them from `$HOME` — they were once written out as the development laptop's paths, which resolve to nothing on the server. It checks that `rclone` and its config exist **before** dumping anything, because an unconfigured host must fail visibly rather than log a success.

**Why only the seed dump goes offsite.** The asset that cannot be recreated is the REVE catalogue — ~12 days of wall-clock under a 5 req/hr cap. Accounts can be recreated by their owners in a minute, so the copy that leaves the machine is the expensive half, and no personal data reaches a third-party processor or needs a retention policy that right-to-erasure would have to reach into. The trade is explicit: **losing the host loses every account.** That is the correct balance only while user rows stay reproducible — the moment [Phase 10](../docs/plan.md) puts a wallet balance or a ledger behind an account, "just register again" stops being true, and the offsite copy must become a full dump encrypted client-side (an `rclone crypt` remote, since B2's server-side encryption leaves the keys with Backblaze).

The `rclone` B2 remote is named `b2`; credentials live in `~/.config/rclone/rclone.conf` (chmod `600`, outside the repo). Restore from offsite:

```bash
rclone copy b2:S-Charge/<file>.dump /tmp/
docker compose exec -T db pg_restore -U ev_charging_app -d ev_charging \
  --clean --if-exists --no-owner < /tmp/<file>.dump
```

Offsite retention is also worth enforcing with a **B2 lifecycle rule** on the bucket (keep only the last version / delete after N days) so hidden versions from prunes don't accumulate.
