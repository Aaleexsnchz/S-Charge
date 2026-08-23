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

**Production's volumes still pin their own `name:`, frozen at what they were created with (`ev-charging-app-prod_*`).** Compose derives a volume's real name from the project name, so renaming the project without a pin points Postgres at a brand-new empty volume while the real one sits orphaned. The pin is what let the project be renamed to `s-charge-prod` without touching the data.

It is a migration aid, not a permanent fixture — and the cost of leaving it is a warning on every `up`:

```
volume "ev-charging-app-prod_postgres_data" already exists but was created
for project "ev-charging-app-prod" (expected "s-charge-prod")
```

Docker cannot relabel a volume in place, so clearing that means copying the data into a correctly-named one. **Dev has been migrated this way and no longer pins anything**; the procedure is below. Do not instead reach for `external: true`: it silences the warning by making the stack refuse to start anywhere the volume does not already exist — every new host, every CI run, every `just prod-up`.

### Renaming a volume

Docker cannot relabel a volume in place, so a rename is a copy. Rehearsed on dev, 2026-08-23.

**Create the new volume with Compose's own labels, or Compose disowns it.** A volume made by a bare `docker volume create` carries no labels and draws a different warning — *"already exists but was not created by Docker Compose"*. Only two labels matter; the `config-hash` Compose also writes is not needed to satisfy it:

```bash
docker volume create \
  --label com.docker.compose.project=s-charge-prod \
  --label com.docker.compose.volume=postgres_data \
  s-charge-prod_postgres_data
```

Nothing may be writing during the copy, so the stack is down for it. **Verify by content, not by size** — `du -sb` differs by a few KB of directory metadata even on an identical copy, so an empty `diff -r` is the real check:

```bash
docker compose -f docker-compose.prod.yml down

docker run --rm -v ev-charging-app-prod_postgres_data:/from:ro \
  -v s-charge-prod_postgres_data:/to alpine sh -c 'cd /from && cp -a . /to/'

docker run --rm -v ev-charging-app-prod_postgres_data:/from:ro \
  -v s-charge-prod_postgres_data:/to:ro alpine diff -r /from /to && echo IDENTICAL
```

Then drop the `name:` pin from the compose file so the volume resolves to `<project>_<declared>`, deploy, and confirm the row counts and `alembic_version` before removing the old volume — keep it until the new one has served real work.

**Fill the new volumes before the compose change reaches the host, not after.** If the pin is removed first, the next `up` creates empty volumes and Postgres initialises a fresh cluster on one — CD then runs `alembic upgrade head` against it and the site serves an empty database until the copy lands. Pre-filling means Compose finds the volume already correct and simply attaches, so the only downtime is the copy plus the deploy.

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

The offsite copy is **Backblaze B2** (bucket `S-Charge`, server-side encryption at rest), uploaded with `rclone`. Only the PII-safe seed dump goes offsite — no `users`/`oauth_account` data ever leaves the machine.

**The server authenticates with its own bucket-scoped application key**, not the laptop's. It is internet-facing, so a key that reaches one bucket of PII-safe dumps is the blast radius worth accepting; it can also be revoked without disturbing anything else. A scoped key cannot `rclone lsd b2:` — listing all buckets is the permission deliberately withheld — so check it with `rclone lsf b2:S-Charge` instead.

**This ran on the development laptop and, until 2026-08-23, on nothing else.** The server had no `rclone`, no config and no cron entry, so from the day it was provisioned there was no offsite copy of the seed at all — every copy lived on the one host. It went unnoticed because the only place it would have said so is a cron log that is written only when the cron exists. Two lessons worth keeping: **a documented backup is not a backup**, and provisioning a host means moving the scheduled work too, not only the service.

[scripts/backup_db_cron.sh](../scripts/backup_db_cron.sh) runs weekly via cron (Mondays 09:00 Madrid, logged to `~/.db-backup.log`): it writes a timestamped seed dump to `backups/`, `rclone copy`s it to B2, and prunes both local and offsite dumps beyond the most recent 8. Cron uses a minimal `PATH` and does not load the profile, so the script sets both `PATH` and `RCLONE_CONFIG` itself, deriving them from `$HOME` — they were once written out as the development laptop's paths, which resolve to nothing on the server. It checks that `rclone` and its config exist **before** dumping anything, because an unconfigured host must fail visibly rather than log a success.

**Why only the seed dump goes offsite.** The asset that cannot be recreated is the REVE catalogue — ~12 days of wall-clock under a 5 req/hr cap. Accounts can be recreated by their owners in a minute, so the copy that leaves the machine is the expensive half, and no personal data reaches a third-party processor or needs a retention policy that right-to-erasure would have to reach into. The trade is explicit: **losing the host loses every account.** That is the correct balance only while user rows stay reproducible — the moment [Phase 10](../docs/plan.md) puts a wallet balance or a ledger behind an account, "just register again" stops being true, and the offsite copy must become a full dump encrypted client-side (an `rclone crypt` remote, since B2's server-side encryption leaves the keys with Backblaze).

The `rclone` B2 remote is named `b2`; credentials live in `~/.config/rclone/rclone.conf` (chmod `600`, outside the repo). Restore from offsite:

```bash
rclone copy b2:S-Charge/<file>.dump /tmp/
docker compose exec -T db pg_restore -U ev_charging_app -d ev_charging \
  --clean --if-exists --no-owner < /tmp/<file>.dump
```

Offsite retention is also worth enforcing with a **B2 lifecycle rule** on the bucket (keep only the last version / delete after N days) so hidden versions from prunes don't accumulate.
