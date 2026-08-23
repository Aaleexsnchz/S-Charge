# Phase 5 — Deployment + CI/CD + releases

Per [plan.md](../plan.md): a secure, phone-accessible HTTPS instance, a complete CI/CD pipeline, and semantic-version releases toward **`v1.0.0` = the build presented for evaluation**. The refresh ETLs ship to the always-on server here but are **not started** — that is [Phase 6](phase-6.md). Architecture and rejected alternatives: [infra-0001](../decisions/infra-0001-deployment.md). Host-level runbook: [setup/deployment.md](../setup/deployment.md).

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Repo-side prod artifacts | Done | #8 |
| 2 | Accounts, host, DNS | Done | host work |
| 3 | Server hardening | Done | host work |
| 4 | Toolchain: lefthook + CI hygiene | Done | #14 |
| 5 | Release plumbing: versioning, CI images, CD, `release.yml` | Done | #16 |
| 6 | Runtime versions + API contract | Done | #18 |
| 7 | First deploy | Done, two operator checks open | host work |
| 8 | External services on the prod origin | Not started | host work |
| 9 | Close the CI/CD loop | Done | #27, #30 |
| 10 | Security gate, cutover, first release | Not started | host work |
| 11 | Renovate | Not started | — |
| 12 | REVE tariff backfill | Moved to [Phase 6](phase-6.md) | — |
| 13 | Auth surface hardening | Done, verify on the host | #19 |
| 14 | Environment configuration | Done | #15 |
| 15 | Authenticate the read endpoints | Done | #20 |
| 16 | Pre-deploy hardening | Done | #21 |

**The application is deployed and publicly reachable at <https://s-charge.app>**, running **`v0.1.0`** (first deployed 2026-08-04; CD proven and tagged 2026-08-21). `main` is PR-protected behind four required checks, a tag push deploys and cuts a GitHub Release, and merging deploys nothing.

**The phase is Done in [plan.md](../plan.md)** on that basis: deployed, released, pipeline proven. The slices still open — 7's two operator checks, 8, 10, 11 and 13's host re-check — are real work that belongs here, but nothing downstream waits on them. `v0.1.0` was therefore tagged when CD was proven, **ahead of Slice 10's gate** rather than after it: the release marks the pipeline working, not the gate passing.

Closed slices are summarised first; what outlives this phase has been migrated to the document that owns it. The open ones keep their detail, at the end.

## Slice 1 — Repo-side prod artifacts [x]

`docker-compose.prod.yml` as a standalone file, the `Caddyfile`, the `scheduler` image stage (supercronic + committed `backend/crontab`) replacing the host refresh crons, env-driven CORS, the root `justfile`, and the provisioning runbook in [setup/deployment.md](../setup/deployment.md). `cd.yml` landed here too, originally triggered by a green CI run on `main` and since changed to a tag push ([infra-0003](../decisions/infra-0003-deploy-on-tag.md)).

## Slice 2 — Accounts, host, DNS [x]

Hetzner server purchased and **`s-charge.app` bought at Cloudflare Registrar**; `A` + `AAAA` records point at the host **DNS-only**, so Caddy can complete the ACME challenge over either protocol. The registrar choice, the HSTS-preload consequence and the rejected `.es` are in [infra-0001](../decisions/infra-0001-deployment.md).

## Slice 3 — Server hardening [x]

Key-only SSH on a non-root `deploy` user, `ufw` limited to SSH + 80/443 on both protocols, `fail2ban` + `unattended-upgrades`, Docker Engine from the official repo, and a dedicated `ed25519` deploy key for CI. Commands and the two gotchas worth keeping — fail2ban's systemd backend, and why the deploy key carries no `command=` restriction — are in [setup/deployment.md](../setup/deployment.md) §1.

**`ufw` does not protect Docker-published ports**; what keeps Postgres private is that `db` has no `ports:` entry at all. Recorded in [operations.md](../operations.md).

## Slice 4 — Toolchain: lefthook + CI hygiene [x]

pre-commit replaced by [lefthook.yml](../../lefthook.yml): staged-file ruff and biome on commit, and a pre-push hook mirroring CI that `just ci` also runs, so the two cannot drift. betterleaks moved to a CI job over full history, leaving the local scan best-effort. CI hygiene closed with it — `--frozen-lockfile`, pnpm single-sourced from `packageManager`, `.nvmrc`, least-privilege `permissions`, caching, and a conditional `concurrency` group.

Why a full CI gate is affordable in a hook — the parallelism measurement — is in [CONTRIBUTING.md](../../CONTRIBUTING.md). The two silent traps it surfaced are commented where they bite, in `lefthook.yml`.

## Slice 5 — Release plumbing [x]

`APP_VERSION` reaches both images as a **build argument**, so it is not runtime configuration and a deploy that forgets to export it reports `dev` until the next rebuild. CI builds the three production image targets. CD dumps the database before `alembic upgrade head`, keeping the last five, and carries `permissions: {}`. `release.yml` turns a tag into a GitHub Release. An image review ran alongside: the frontend gained the `HEALTHCHECK` it lacked, `python:*-slim` was single-sourced to an `ARG`, and nginx moved to the unprivileged image on 8080.

Policy is [infra-0002](../decisions/infra-0002-manual-release-tagging.md); the image stages and their sizes are in [operations.md](../operations.md); rollback and the migration window — the half git cannot undo — are in [setup/deployment.md](../setup/deployment.md). Digest pinning deferred to [Slice 11](#slice-11--renovate).

## Slice 6 — Runtime versions + API contract [x]

Python 3.13 everywhere, including `backend/.python-version`, which decides the interpreter `uv` builds the local environment with. The dev database moved to Postgres 18 with identical row counts and the stuck REVE watermark preserved at `2026-07-08 19:30:03`. `openapi.json` is exported by `scripts/export_openapi.py`, committed, and gated at two levels — the schema must match the app, and the generated types must match the schema — both verified to fail on a real drift.

**`uuidv7()` was evaluated and rejected**; the reasoning is in [tech-stack.md](../tech-stack.md), and the mount-path trap a major Postgres upgrade carries is in [operations.md](../operations.md).

## Slice 9 — Close the CI/CD loop [x]

Repo secrets set, and a branch-protection ruleset active on `main`: PR required, four required checks, no force-push, no deletion. **Zero approvals** — a solo developer cannot approve their own PR, and any higher number locks the repository. Verified end to end **both ways**: merging deploys nothing, a tag push deploys and reports that tag at `/api/health`.

Two pipeline defects were found doing it, both fixed and both commented where they bite in `cd.yml`: the remote script exited 0 without deploying because `compose exec -T` consumed the heredoc that `bash -s` was reading, and an HTTPS remote on the host cannot fetch a private repository unattended.

## Slice 12 — REVE tariff backfill → moved to [Phase 6](phase-6.md)

Turning the ETLs on is a decision about a frozen watermark and an unmeasured 504, not a step of a deploy. The probing plan and the measured ceiling moved to [phase-6.md](phase-6.md). What this phase owed it was **not touching the watermark**, which the stopped `scheduler` profile guarantees structurally rather than by memory.

## Slice 14 — Environment configuration [x]

One `.env` at the repository root, with `.env.example` as its committed twin and the only documentation of what configuration exists. The frontend keeps no env file — Vite's `envDir` staying put is what makes it structurally impossible for a backend secret to reach the bundle. `ENVIRONMENT=production` arms a boot check, because `secret_key` defaulted to the empty string and signs every session: a missing line failed *open*. A test asserts `Settings` and `.env.example` describe the same set, so a setting cannot ship undocumented.

**Compose truncates an env value at the first `$` and only warns** — recorded in [setup/deployment.md](../setup/deployment.md).

## Slice 15 — Authenticate the read endpoints [x]

Every `/api/*` route except `/api/health` and the auth surface now requires a session, applied at the `include_router` calls rather than per route, where one new endpoint would silently miss it. This was the backend catching up with a decision the frontend had already made: `points`, `prices`, `simulate` and `vehicles` carried no user dependency, so anyone holding the URL could pull the full catalogue while a real user was made to log in for the same data.

The regression guard reads `app.openapi()["paths"]` rather than a hand-written list, so a router mounted unguarded fails it rather than shipping open. Its consequence for the [REVE data-rights question](../production-readiness.md) is recorded there.

**Not done:** a browser click-through after login — the one claim resting on argument rather than a run.

## Slice 16 — Pre-deploy hardening [x]

The OWASP header set on every Caddy response, **minus two deliberate omissions**: `Cross-Origin-Embedder-Policy: require-corp` would block the OpenFreeMap tiles, and `geolocation=()` would kill `useGeolocation`. The CSP carries only `frame-ancestors 'none'`; the rest is [Phase 13](../plan.md), blocked on MUI and Emotion injecting inline styles. `cryptography` bumped for [CVE-2026-69247](https://advisories.gitlab.com/pypi/cryptography/CVE-2026-69247/); `pip-audit` clean afterwards. Interactive docs disabled under `ENVIRONMENT=production` — defence in depth, since Caddy forwards only `/api/*` and they were never reachable.

Two backup defects fixed: the cron script hardcoded the laptop's `$HOME` for `rclone` and its config, and the dump had no size check — the 0-byte dump that reached the offsite bucket on 2026-07-13 is [recorded in operations.md](../operations.md).

**Not addressed, deliberately:** the 14-day session with no revocation ([auth-0002](../decisions/auth-0002-cookie-session.md)), the deploy key with no `command=` restriction, and the boot check verifying `SECRET_KEY` differs from the placeholder without checking it is strong. All three are known and recorded.

---

## Slice 7 — First deploy

**Acceptance:** the app loads over HTTPS on a phone, the PWA installs, `/api/health` reports ok with a version, and **the `scheduler` service is not running** — deliberately, not by accident.

Live on the host since 2026-08-04. Runbook: [setup/deployment.md](../setup/deployment.md) §3–5.

- [x] Repo cloned to `/opt/s-charge` **over SSH**, using a read-only repository deploy key — an HTTPS remote cannot authenticate unattended and breaks CD at `git fetch`
- [x] Database bootstrapped from `ev_charging_seed_20260803T070005Z.dump` — **never re-seed**, the REVE catalogue takes ~12 days under the 5 req/hr cap
- [x] `up -d --build` + `alembic upgrade head`, `scheduler` confirmed absent
- [ ] The server-side `.env` written with **every secret rotated**. `ENVIRONMENT=production` arms the boot check, so the app being up proves the check passed — not that the values are fresh
- [ ] Verified on a phone: the site loads and the PWA installs

**The cost of the stopped scheduler, accepted:** the seed's price curve stops at `2026-08-01 21:00 UTC`, so `/api/prices/today` and the dashboard sit on an empty state until [Phase 6](phase-6.md). PVPC itself is fully backfilled in the seed — the 29-day hole from 2026-07-03 healed in one local run, because `fetch_pvpc.py` gap-backfills and REE serves history.

**The weekly backup could not be verified here** and waits on [Slice 10](#slice-10--security-gate-cutover-first-release): `backup_db.sh` runs a bare `docker compose exec -T db`, which resolves the dev compose project and finds no `db` on the server, and it falls back to the development database credentials. Both are fixed from the crontab entry rather than in code.

## Slice 8 — External services on the prod origin

**Acceptance:** Google sign-in and verification email both work against the production domain, for users other than the account owner.

- [ ] Google OAuth client: `https://s-charge.app` as authorised origin, `https://s-charge.app/api/auth/google/callback` as redirect URI
- [ ] **Consent screen published to Production** — scopes are non-sensitive (`userinfo.profile`, `userinfo.email`), so no Google verification and no warning screen; while in Testing only listed test users can sign in
- [ ] Resend: sending domain verified, `MAIL_FROM` set — without it verification mail only reaches the owner's inbox
- [ ] `up -d --force-recreate backend` (Compose snapshots env at container creation; a restart keeps stale values)

## Slice 10 — Security gate, cutover, first release

**Acceptance:** the infra-0001 pre-deploy gate passes and the laptop is no longer part of production.

- [ ] `/security-review` run; infra-0001 gate passed (HSTS, only 22/80/443 open, no published `5432`, secrets rotated, cookie `Secure`, CORS empty, backup restorable, auth endpoints rate-limited and logging the real client IP per [Slice 13](#slice-13--auth-surface-hardening))
- [ ] Laptop crontab refresh/PVPC lines removed — the scheduler container owns them now
- [ ] `backup_db_cron.sh` moved to the server crontab (needs `rclone` + B2 config on the VPS), and **`backup_db.sh` pointed at the right compose project**: `COMPOSE_FILE=docker-compose.prod.yml` in the crontab entry is the whole fix, and the production database credentials have to come with it or the dump names a database that is not there. Run it once by hand before trusting the schedule
- [x] **`v0.1.0` tagged** (2026-08-21)
- [ ] infra-0001 flipped to `accepted`. **The B2 bucket moved to `S-Charge` on 2026-08-23** with a *keep only the last version* lifecycle rule and a bucket-scoped key for the server; `tfm-db-backups` is superseded

## Slice 11 — Renovate

**Acceptance:** Renovate opens grouped dependency PRs on a weekly schedule, gated by the same CI as any other PR.

Unblocked — Slice 9 is done, so the first automated PRs arrive against a pipeline already proven end to end. Everything this phase found by hand (a deprecated Node runtime twice, pnpm 10 vs 11 drift, uv pinned differently in CI and the Dockerfile, nginx four minors stale) is a PR Renovate would have opened instead.

- [ ] Renovate GitHub App installed on the repository
- [ ] `renovate.json`: weekly schedule, non-majors grouped into one PR, dev dependencies grouped, majors one at a time, dependency dashboard, `:semanticCommits` so PR titles match the Conventional Commits rule
- [ ] Scope includes `github-actions` and the Docker base images, not just `uv`/`pnpm` manifests
- [ ] **Pin base images by digest** once Renovate is maintaining them. Every `FROM` is on a floating tag today, so a rebuild can silently change the patch version — pinning by hand before a bot maintains the digests trades one drift for a worse one
- [ ] `vulnerabilityAlerts` unscheduled, so security updates are not held for the weekly window
- [ ] No automerge — every dependency PR merges by hand and reaches production with the next tag ([infra-0003](../decisions/infra-0003-deploy-on-tag.md))

## Slice 13 — Auth surface hardening

**Acceptance:** the authentication endpoints are rate-limited, and the IP recorded in the auth audit log is the real client's rather than the reverse proxy's.

Done in the repository. Auth endpoints are rate-limited per IP and per path, uvicorn trusts Caddy's forwarded headers via `--forwarded-allow-ips=172.16.0.0/12` rather than `*`, and container log retention is capped because those logs now carry real client IPs. The decision, the limits chosen and the data-protection position: [auth-0004](../decisions/auth-0004-rate-limits-and-client-ip.md).

Verified locally against a real proxy chain — the prod image behind `caddy:2.11-alpine`, two persistent client containers on distinct addresses getting separate counters. Short-lived probe containers do *not* work as separate clients: Docker recycles the freed address, so every probe reuses one IP and the run looks exactly like the bug.

- [ ] Re-check on the deployed instance, where the client address is a real public IP rather than a Docker one. Part of [Slice 10](#slice-10--security-gate-cutover-first-release)'s gate

## Open decision

Whether to keep registration invite-only during the demo window. Email verification already blocks drive-by signups, so this is a judgement call rather than a gap — decide before the URL is shared.
