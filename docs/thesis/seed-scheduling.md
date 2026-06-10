---
status: draft (thesis writeup, concept-level)
---

# Seed scheduling — cron + the per-tick contract

The REVE catalogue ETL runs on host-side cron: a single line invokes the `seed_reve` orchestrator inside the backend container, which spends up to five REVE calls per hour and exits. Over ~12 days of unattended ticks the full Spanish catalogue lands in Postgres. Once the four `reve_etl_cursor` rows all carry a `completed_at`, the same cron line becomes the daily-refresh hook described in [PLAN.md](../PLAN.md) without a code change. See [phases/phase-2.md](../phases/phase-2.md) for the slice criteria.

## Why a scheduler is necessary

REVE caps at five requests per hour per credential. A live request-time proxy is impossible — one cold map load consumes the entire hour's allowance. A single bootstrap script is also impossible — hundreds of paginated calls are needed at thesis scale. The whole ETL shape (staged endpoints, cursor table, per-tick budget) falls out of that 5-req/hr rule.

## Why cron over alternatives

- *In-process scheduler (APScheduler in the FastAPI lifespan).* Container restarts and `uvicorn --reload` reset in-memory state; a DB-backed job store duplicates the role of `reve_etl_cursor`.
- *Single long-lived bootstrap script.* Either ignores the rate limit (and 429-throttles to a halt) or sleeps twelve minutes between calls for twelve days as a single point of failure.
- *Windows Task Scheduler.* Bypasses WSL idle but isn't reproducible from the repo. Held as the upgrade path if WSL-idle losses become significant.

Cron is the smallest primitive that meets the constraint: declarative schedule, persists across reboots, one independent process per tick, no shared state.

## The tick contract

Each tick is **bounded** (≤5 REVE calls, picks the next uncompleted endpoint in dependency order `/cpos → /locations → /connectors/tariffs → /evses/operational_status`, exits cleanly on `429`) and **idempotent** (all four endpoint imports use Postgres `INSERT … ON CONFLICT DO UPDATE` keyed on the source ID; a re-run of an already-fetched page updates rows in place). That combination is what makes "one short process per hour" the right abstraction: missed ticks are recovered by the next, crashed ticks cost nothing.

## Operating it

```bash
# Install (one-time) — runs at minute 30 of every hour.
(crontab -l 2>/dev/null; echo "30 * * * * /usr/bin/docker compose -f /home/aaleexsnchz/tfm/docker-compose.yml exec -T backend uv run python -m scripts.seed_reve >> /home/aaleexsnchz/.reve-seed.log 2>&1") | crontab -

# Verify
crontab -l

# Check progress (no API call)
docker compose exec backend uv run python -m scripts.seed_reve --status
tail -n 20 ~/.reve-seed.log

# Stop
crontab -r            # remove all entries, or
crontab -e            # edit / comment the line
```

Each tick appends one JSON audit line per endpoint touched plus a closing `calls used: N/5` summary to `~/.reve-seed.log`. The crontab persists across reboots; cron starts automatically because `systemd=true` is set in `/etc/wsl.conf` and `cron.service` is `enabled`.

## WSL2 idle caveat

When no shell is open against the WSL distro, systemd inside it suspends and cron does not fire. A laptop closed for eight hours costs eight ticks (~4 000 catalogue rows of progress) — the cursor is unharmed and the next live tick resumes. Acceptable for a thesis defended on a personal laptop; the mitigation, if needed, is Windows Task Scheduler firing `wsl --distribution <name> docker compose …`.
