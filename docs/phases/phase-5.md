# Phase 5 — Deployment + CI/CD + releases

Per [plan.md](../plan.md): a secure, phone-accessible HTTPS instance with the refresh ETLs shipped to an always-on server (started in [Phase 7](../plan.md), not here), a complete CI/CD pipeline, and semantic-version releases toward **`v1.0.0` = the build presented for evaluation**. Architecture and rejected alternatives: [infra-0001](../decisions/infra-0001-deployment.md). Host-level runbook: [setup/deployment.md](../setup/deployment.md).

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Repo-side prod artifacts | Done | #8 |
| 2 | Accounts, host, DNS | Done | host work |
| 3 | Server hardening | Done | host work |
| 4 | Toolchain: lefthook + CI hygiene | Done | #14 |
| 5 | Release plumbing: versioning, CI images, CD, `release.yml` | Done | #16 |
| 6 | Runtime versions + API contract | Done | #18 |
| 7 | First deploy | Done | host work |
| 8 | External services on the prod origin | Not started | host work |
| 9 | Close the CI/CD loop | Not started | — |
| 10 | Security gate, cutover, first release | Not started | host work |
| 11 | Renovate | Not started | — |
| 12 | REVE tariff backfill | Moved to [Phase 7](../plan.md) | — |
| 13 | Auth surface hardening | Code done, verify on the host | #19 |
| 14 | Environment configuration | Done | #15 |
| 15 | Authenticate the read endpoints | Done | #20 |
| 16 | Pre-deploy hardening | Done | #21 |

Numbering is not the running order. **Slices 13 and 15 must land before [Slice 10](#slice-10--security-gate-cutover-first-release)**, whose gate checks for what they fix; they and Slice 14 are numbered last only because they were found after the plan was written.

**Where things stand:** **the application is deployed and publicly reachable at <https://s-charge.app>** (Slice 7, 2026-08-04). Verified from outside the host on 2026-08-05: HTTPS with HSTS, the full security-header set, `Permissions-Policy`, `/api/points` answering `401` without a session, and the interactive docs disabled in production.

What remains: **Slices 8 → 9 → 10**, then 11. The `scheduler` service is deployed but **deliberately not started** — it sits behind a Compose profile so a deploy cannot move the REVE watermark by accident, so the REVE/PVPC refresh **still has not run since early July** ([Phase 7](../plan.md) owns turning it back on). **No tag has been pushed**, so `/api/health` reports the commit hash rather than `v0.1.0`, and the CD workflow stays inert until one is. `main` is not yet PR-protected, though changes are already going through PRs by convention.

## Start here

**Everything that does not need the host is done** — Slices 1, 4, 5, 6, 13, 14, 15 and 16, plus the two local commands that healed the PVPC curve and re-took the seed dump before production is bootstrapped from it. **Slice 7 is done too: the stack is live on the host.**

**What remains, in order: 8 → 9 → 10**, ending at `v0.1.0`. Then 11.

- **8 → 9 → 10 is a chain on the host**, each step depending on the one before.
- **[13](#slice-13--auth-surface-hardening) carries one item into that chain**: its two fixes only exist behind the proxy, so they are verified on the live host as part of Slice 10's gate.
- **11 last.** Renovate wants a pipeline already proven end to end. Slice 12 is no longer part of this phase — the tariff backfill became [Phase 7](../plan.md).

**Why this phase comes before the frontend migration** (Phase 6), in case it is asked again: the migration benefits from nearly every slice here — CI building the frontend prod image catches a broken build on the PR that caused it, the committed `openapi.json` stops the rewrite drifting from the API, the pre-push hook covers ~3,200 lines of churn, and a deploy on demand means each migration slice can be opened on a phone, which is the only way to check the one risk no tool verifies. Deployment gains nothing from the migration in return: nginx serves a `dist/` and does not care what is in it. Separately, the REVE tariff gap widens permanently every day the server does not exist.

## Decisions taken

- **Host: a 2 vCPU / 4 GB x86-64 EU VPS on Ubuntu 26.04, on Hetzner** — CX23 if in stock, else CPX22. The spec is the decision; the SKU is a purchasing detail. Fallback providers and why arm64 and GCP stay out: [infra-0001](../decisions/infra-0001-deployment.md).
- **A real registered domain** (~€10/yr) over a free DuckDNS subdomain. `duckdns.org` sits on the Public Suffix List, so Google treats the subdomain as the top private domain and wants it verified before accepting it as an OAuth authorised domain. A registrable domain removes that friction and reads better at the defense.
- **Prod images build in CI**, not only on the VPS. As built, a change that breaks either Dockerfile passes CI green and fails on the server at deploy time.
- **Releases are tagged manually**, version derived from the tag — [infra-0002](../decisions/infra-0002-manual-release-tagging.md).
- **A tag push deploys; merging does not** — [infra-0003](../decisions/infra-0003-deploy-on-tag.md), decided mid-phase and superseding the "deploy on merge to `main`" criterion in [plan.md](../plan.md). The manual run of the CD workflow covers looking at unreleased work on a phone, which is what the frontend migration needs.

## Release policy

Recorded permanently in [infra-0002](../decisions/infra-0002-manual-release-tagging.md): manual tags, version derived from `git describe`, no changelog file, and why `release-please` was evaluated and reversed. This phase only *implements* it — `release.yml` and the version stamping are [Slice 5](#slice-5--release-plumbing).

## Slice 1 — Repo-side prod artifacts [x]

`docker-compose.prod.yml` as a standalone file, the `Caddyfile`, the `scheduler` image stage (supercronic + committed `backend/crontab`) replacing the host refresh crons, env-driven CORS, the root `justfile`, and the provisioning runbook in [setup/deployment.md](../setup/deployment.md). `cd.yml` landed here too, originally triggered by a green CI run on `main` and since changed to a tag push ([infra-0003](../decisions/infra-0003-deploy-on-tag.md)).

## Slice 2 — Accounts, host, DNS [x]

Hetzner account verified, server purchased, and **`s-charge.app` bought at Cloudflare Registrar** — the choice, the HSTS-preload consequence and the rejected `.es` are in [infra-0001](../decisions/infra-0001-deployment.md). `A` + `AAAA` records point at the host **DNS-only**, verified against Cloudflare's authoritative nameservers to resolve to the Hetzner box rather than an anycast address, so Caddy can complete the ACME challenge over either protocol.

## Slice 3 — Server hardening [x]

Key-only SSH on a non-root `deploy` user, `ufw` limited to SSH + 80/443 on v4 and v6, `fail2ban` + `unattended-upgrades`, Docker Engine from the official repo, and a dedicated `ed25519` deploy key for CI. Verified from outside the host that every account answers `Permission denied (publickey)`. Commands and the two gotchas worth keeping — fail2ban's systemd backend, and why the deploy key carries no `command=` restriction — are in [setup/deployment.md](../setup/deployment.md) §1.

**`ufw` does not protect Docker-published ports.** Docker's DNAT rules are evaluated before ufw's INPUT chain, so a `ports:` entry is reachable from the internet while `ufw status` still looks correct. What keeps Postgres private is that `docker-compose.prod.yml` gives `db` no `ports:` entry at all — not the firewall. The SSH tunnel that replaces it is in [operations.md](../operations.md).

## Slice 4 — Toolchain: lefthook + CI hygiene [x]

pre-commit replaced by [lefthook.yml](../../lefthook.yml): staged-file ruff and biome with auto-restage on commit, and a pre-push hook mirroring CI that `just ci` also runs, so the two lists cannot drift. The whole battery takes **8 s** of wall time against ~29 s of CPU because the jobs run in parallel — the measurement that decided a full CI gate could live in a hook, and it is in [migracion-del-stack.md](../thesis/migracion-del-stack.md). betterleaks moved to a CI job over full history, leaving the local scan best-effort.

CI hygiene closed with it: `--frozen-lockfile`, the pnpm version single-sourced from `packageManager`, `.nvmrc`, least-privilege `permissions`, dependency caching, and a `concurrency` group whose `cancel-in-progress` is conditioned on the event so a superseded run on `main` is never cancelled.

The two silent traps it surfaced are commented where they bite, in `lefthook.yml`: ruff ignores its own exclude list when paths are passed explicitly, and lefthook's default glob matcher reads `**` as *one or more* directory levels, which silently skipped `frontend/package.json`.

## Slice 5 — Release plumbing [x]

`APP_VERSION` reaches both images as a **build argument** — Vite inlines it and the backend bakes it in, so it is not runtime configuration and a deploy that forgets to export it reports `dev` until the next rebuild. CI builds the three production image targets, so a broken Dockerfile fails on the pull request rather than at deploy time. CD dumps the database before `alembic upgrade head`, keeping the last five, and carries `permissions: {}`. `release.yml` turns a tag into a GitHub Release.

Rollback and the migration window are written down in [setup/deployment.md](../setup/deployment.md), including the half git cannot undo: code rolls back, the schema does not.

**Image review**, done alongside: the frontend gained the `HEALTHCHECK` it lacked, `python:*-slim` was single-sourced to an `ARG`, and nginx later moved to the unprivileged image on 8080. Digest pinning was deferred to [Slice 11](#slice-11--renovate), where a bot can maintain it. Sizes: backend `prod` 330 MB, `scheduler` 356 MB, frontend `prod` 77.5 MB.

## Slice 6 — Runtime versions + API contract [x]

Python 3.13 everywhere, including `backend/.python-version`, which decides the interpreter `uv` builds the local environment with and was not on the original list. The dev database moved to Postgres 18 with **identical row counts** and the stuck REVE watermark preserved at `2026-07-08 19:30:03`, which [Slice 12](#slice-12--reve-tariff-backfill) probes from.

`openapi.json` is exported by `scripts/export_openapi.py`, committed, and gated at two levels: the schema must match the app, and the generated types must match the schema. Both were verified to fail on a real drift. The export sorts keys, so regeneration is reproducible.

**`uuidv7()` was evaluated and rejected** — its gain is insert locality, and the largest table is ~47k rows seeded once against roughly two dozen inserts a day. The reasoning is in [migracion-del-stack.md](../thesis/migracion-del-stack.md) as a *camino no tomado*; the mount-path trap a major upgrade carries is in [operations.md](../operations.md).

## Slice 7 — First deploy

**Acceptance:** the app loads over HTTPS on a phone, the PWA installs, `/api/health` reports ok with a version, and **the `scheduler` service is not running** — deliberately, not by accident.

**The ETLs stay off until [Phase 7](../plan.md).** Turning them on is a decision about REVE's frozen watermark and a 504 that still needs measuring, and it should not ride along with a deploy. The mechanism is a Compose profile on the `scheduler` service, so `docker compose up -d` skips it and `cd.yml` needs no flag it could forget; enabling it later is `--profile scheduler up -d`. CI is unaffected, since it builds that image with `docker build --target scheduler` rather than through Compose. **The cost is that `/api/prices/today` returns nothing from the day of the deploy** — the seed's curve stops at `2026-08-01 21:00 UTC` — so the prices and dashboard views sit on an empty state until Phase 7. That is accepted, not overlooked.

Full detail in [setup/deployment.md](../setup/deployment.md) §3–5.

- [ ] Repo cloned to `/opt/tfm` (the path `cd.yml` assumes)
- [ ] The server-side `.env` written with **every secret rotated** — fresh `SECRET_KEY`, new `POSTGRES_PASSWORD`, `ENVIRONMENT=production`, `APP_DEBUG=false`, `SESSION_COOKIE_SECURE=true`, empty `CORS_ALLOW_ORIGINS`, prod `APP_BASE_URL` / `GOOGLE_REDIRECT_URI`, `SITE_ADDRESS`; copies kept in a password manager, and **no value containing `$`** ([Slice 14](#slice-14--environment-configuration)). `ENVIRONMENT=production` arms the boot check, so a misconfigured file now restart-loops the backend instead of serving with a development secret
- [ ] Database bootstrapped from `backups/ev_charging_seed_20260803T070005Z.dump` — **never re-seed**, the REVE catalogue takes ~12 days under the 5 req/hr cap
- [ ] `up -d --build` + `alembic upgrade head`
- [ ] Verified: site on a phone, PWA installs, `/api/health` returns the version, and `docker compose -f docker-compose.prod.yml ps` shows **no** `scheduler` container

**Not verified here: the weekly backup.** Running `./scripts/backup_db_cron.sh` on the server was going to be this slice's last step, and it cannot pass yet — `backup_db.sh` invokes a bare `docker compose exec -T db pg_dump`, which resolves `docker-compose.yml` and its dev project, where the server has no running `db`. `COMPOSE_FILE=docker-compose.prod.yml` in the environment fixes it with no code change (Compose reads that variable, and it correctly skips the `scheduler` profile), and the database credentials have to come with it, since the script falls back to the development names. It also needs `rclone` and its B2 config on the host, which arrives with the crontab cutover in [Slice 10](#slice-10--security-gate-cutover-first-release). Both belong with the host-script pass there, not wedged into a first deploy. This is the same class of defect [Slice 16](#slice-16--pre-deploy-hardening) caught in the `$HOME` paths — a laptop assumption that fails into a cron log nobody reads — and it survived because that audit checked the paths and not the compose project.

### Closing the data gap

The ETLs stopped when the laptop did. The PVPC hole is closed; the REVE one is measured as of 2026-08-01 and keeps growing until the scheduler runs on the server.

- [x] **PVPC prices — recoverable, backfilled.** The hole ran from **2026-07-03** to 2026-08-01, 29 days. `fetch_pvpc.py` gap-backfills from the last stored hour to tomorrow and REE serves history, so it healed completely in one local run ([Step 0](#start-here)) — production is bootstrapped from a seed dump that already contains the full curve. It does not stay current on its own — the curve ends where the dump ends until the scheduler comes on, which is the empty state [Slice 7](#slice-7--first-deploy) accepts
- [ ] **REVE tariffs — nothing happens here any more.** The recovery is [Phase 7](../plan.md). What this phase owes it is *not touching the watermark*: it is still parked at **2026-07-08 19:30** because the 504 hit while it was recent and it was classed transient, and the first unattended refresh tick would jump it to `now − REVE_REFRESH_LOOKBACK_HOURS`, destroying the value Phase 7 probes from. Deploying with the `scheduler` profile off is what protects it — the ordering constraint that used to live here is now structural rather than remembered
- [x] **Re-take the seed dump after the PVPC backfill**, so production starts from the freshest catalogue. The bootstrap artifact is **`ev_charging_seed_20260803T070005Z.dump`**, the weekly cron's snapshot, and **it cannot go stale while it waits**: both ETLs are off on the laptop too, so every dump taken since carries the same rows — the price curve still ends `2026-08-01 21:00 UTC` and the watermark still reads `2026-07-08 19:30:03`. There is nothing to gain by re-taking it closer to the deploy
- [ ] After the first scheduler ticks, confirm in the logs that both jobs ran, that `electricity_prices` reaches today, and whether `reve_refresh_jumped_to_recent` fired

## Slice 8 — External services on the prod origin

**Acceptance:** Google sign-in and verification email both work against the production domain, for users other than the account owner.

- [ ] Google OAuth client: `https://<domain>` as authorised origin, `https://<domain>/api/auth/google/callback` as redirect URI
- [ ] **Consent screen published to Production** — scopes are non-sensitive (`userinfo.profile`, `userinfo.email`), so no Google verification and no warning screen; while in Testing only listed test users can sign in
- [ ] Resend: sending domain verified, `MAIL_FROM` set — without it verification mail only reaches the owner's inbox
- [ ] `up -d --force-recreate backend` (Compose snapshots env at container creation; a restart keeps stale values)

## Slice 9 — Close the CI/CD loop

**Acceptance:** merging a PR to `main` deploys to production automatically, and `main` cannot be pushed to directly or force-pushed.

- [ ] Repo secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS` (`ssh-keyscan <host>`)
- [x] CD workflow enabled in the Actions tab — safe to do before the server exists now that it only fires on a tag push or a manual run ([infra-0003](../decisions/infra-0003-deploy-on-tag.md)), so nothing can trigger it by accident
- [ ] Branch protection ruleset on `main`: **require a pull request**, require the CI checks, block force-push and deletion
- [ ] **End-to-end test:** trivial PR → merge → CI green → **nothing deploys** → push a tag → CD deploys → `/api/health` reports that tag. Both halves matter: that merging is inert is as much a claim to verify as that tagging ships ([infra-0003](../decisions/infra-0003-deploy-on-tag.md)).

## Slice 10 — Security gate, cutover, first release

**Acceptance:** the infra-0001 pre-deploy gate passes, the laptop is no longer part of production, and `v0.1.0` is tagged.

- [ ] `/security-review` run; infra-0001 gate passed (HSTS, only 22/80/443 open, no published `5432`, secrets rotated, cookie `Secure`, CORS empty, backup restorable, auth endpoints rate-limited and logging the real client IP per [Slice 13](#slice-13--auth-surface-hardening))
- [ ] Laptop crontab refresh/PVPC lines removed — the scheduler container owns them now
- [ ] `backup_db_cron.sh` moved to the server crontab (needs `rclone` + B2 config on the VPS), and **`backup_db.sh` pointed at the right compose project** — it runs a bare `docker compose exec -T db`, which resolves the dev file and finds nothing on the server. `COMPOSE_FILE=docker-compose.prod.yml` in the crontab entry is the whole fix; see [Slice 7](#slice-7--first-deploy). It also **defaults `POSTGRES_USER` and `POSTGRES_DB` to the development names**, which production does not use — the crontab entry has to supply the server's, or the dump names a database that is not there. Verify by running it once by hand before trusting the schedule
- [ ] **`v0.1.0` tagged**
- [ ] infra-0001 flipped to `accepted`; B2 lifecycle rule added on `tfm-db-backups`

## Slice 11 — Renovate

**Acceptance:** Renovate opens grouped dependency PRs on a weekly schedule, and they are gated by the same CI as any other PR.

Lands **after** Slice 9, so the first automated PRs arrive against a pipeline that is already proven end to end. The Phase 5 toolchain-hygiene list above — deprecated Node runtime, pnpm 10 vs 11 drift, uv pinned differently in CI and the Dockerfile — is a list of things Renovate would have raised as PRs instead of being found by hand.

- [ ] Renovate GitHub App installed on the repository
- [ ] `renovate.json`: weekly schedule, non-majors grouped into one PR, dev dependencies grouped, majors one at a time, dependency dashboard, `:semanticCommits` so PR titles match the Conventional Commits rule
- [ ] Scope includes `github-actions` and the Docker base images, not just `uv`/`pnpm` manifests
- [ ] **Pin base images by digest** once Renovate is maintaining them. Every `FROM` is on a floating tag today (`python:3.13-slim`, `nginxinc/nginx-unprivileged:1.27-alpine`, `caddy:2.11-alpine`, `postgres:18-alpine`), so a rebuild can silently change the patch version. Pinning by hand before there is a bot to update the digests trades one drift for a worse one
- [ ] `vulnerabilityAlerts` unscheduled, so security updates are not held for the weekly window
- [ ] No automerge — every dependency PR merges by hand and reaches production with the next tag ([infra-0003](../decisions/infra-0003-deploy-on-tag.md))

## Slice 12 — REVE tariff backfill — moved to Phase 7

**This slice does not run in Phase 5.** It became [Phase 7](../plan.md), because turning the ETLs on is a decision about a frozen watermark and an unmeasured 504, not a step of a deploy. The method below is kept here rather than deleted — it is the probing plan Phase 7 starts from, and it is the only part of this phase whose outcome is not under the project's control.

**Acceptance (in Phase 7):** the tariff watermark has been advanced from 2026-07-08 by the largest span REVE will actually serve, the unrecoverable remainder is measured rather than assumed, and both numbers are written into [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).

**The constraint.** `/connectors/tariffs` takes `date_from` and no `date_to`, so a stale range cannot be sliced into chunks — the only lever is *how far back `date_from` points*. A wide window makes REVE scan too much and time out; a narrow one returns quickly but recovers less history. There is therefore no way to backfill the gap in pieces, and the whole slice reduces to one measurement: **the oldest `date_from` REVE will answer with a 200.** Everything older than that is unrecoverable through this endpoint at any price.

Note that the gap is **self-healing per connector, but only forward**: any connector whose tariff changes after the deploy re-emits its current price on the next tick. What is lost is the intermediate history of connectors that changed during the gap and then went quiet — the stored price is stale until that connector next moves.

The production database inherits the stuck watermark from the seed dump (`reve_etl_cursor` is in the archive), so the probe runs against the same starting point locally and on the server.

**Expect to recover almost none of it.** The ceiling was already measured once under controlled conditions ([precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md)): `date_from` at ~100 h, ~20 h and intermediate values all returned 504, while `now − 3 h` returned 200. The servable window is **hours wide**, so a ~24-day gap is written off almost in full unless REVE's performance has changed since. This slice exists to turn "almost in full" into a number, not to rescue the data.

- [ ] **Stop the scheduler before probing by hand.** Every probe below is a second writer against `reve_etl_cursor` while the hourly cron ticks, and two concurrent runs corrupt the watermark — the field whose loss caused this gap in the first place. `docker compose -f docker-compose.prod.yml stop scheduler` for the duration, and start it again after. The permanent fix is an advisory lock, deferred to Phase 13 ([production-readiness.md](../production-readiness.md)); until it lands, this is a manual discipline
- [ ] `--date-from` override on `refresh_reve.py`, so the watermark can be aimed deliberately instead of edited with raw SQL. `--status` already exists to read it back
- [ ] **One optimistic probe first**: `date_from = 2026-07-08`. One call. If REVE has fixed the wide-window regression it answers 200, the gap closes entirely and the rest of this slice is a drain. Cheap enough that not testing it would be careless — but the prior measurement says not to plan around it
- [ ] **Then bracket the real ceiling**: binary-search between `now − 3 h` (known 200) and `now − 20 h` (known 504). ~3 probes at 5 calls/hr. Do this **before** an unattended tick jumps the watermark — see [Closing the data gap](#closing-the-data-gap)
- [ ] Set the watermark to the oldest instant that answered and let the normal budgeted drain paginate through it. No special-case code path: this is the ordinary refresh loop pointed at an older start
- [ ] **Record the measured gap** — the span recovered and the span written off — in [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md), and re-check whether the 3 h/20 h bracket still holds a second time. A documented hole with a number is a finding; an undocumented one is a defect
- [ ] If the ceiling has moved materially since the first measurement, `REVE_REFRESH_LOOKBACK_HOURS` should move with it — it is currently 2 h, chosen as a span known to answer 200

**Open question:** whether to re-probe periodically or accept the first measurement as final. The 504 is a REVE-side performance regression that has self-healed once before, so a window that fails today may succeed later — but the recoverable history ages out meanwhile, and by the defense the gap is historical either way. Decide once the first probe has a number.

## Slice 13 — Auth surface hardening

**Acceptance:** the authentication endpoints are rate-limited, and the IP recorded in the auth audit log is the real client's rather than the reverse proxy's.

Repo work, independent of the host, so it runs alongside Slices 4–6. **It must land before [Slice 10](#slice-10--security-gate-cutover-first-release)**: both items are things that slice's gate checks for, and both are only reachable-from-the-internet problems, so they cost nothing while the app is on a laptop and matter the moment a URL is shared.

Both were found by reading the production artifacts against the [infra-0001](../decisions/infra-0001-deployment.md) gate, not by a tool. Neither is a regression — they have never worked.

Decision, limits chosen and the data-protection position: [auth-0004](../decisions/auth-0004-rate-limits-and-client-ip.md).

- [x] **Rate-limit the auth endpoints.** Per IP and per path, as a dependency on each `include_router`: 10/minute on login, 10/hour on registration, 5/hour on the mail-sending routers. `slowapi` **does** work here via the route-mutation pattern from the `fastapi-users` discussions (measured: `[201, 400, 400, 429, 429]` at `3/minute`) — it was rejected because that pattern matches library-internal path strings and silently limits nothing when one is renamed. Dropped from the dependencies, `limits` promoted to a direct one
- [x] **Trust Caddy's forwarded headers.** `--forwarded-allow-ips=172.16.0.0/12` on the `prod` stage `CMD`, **not `*`**: the wildcard makes uvicorn take the leftmost `X-Forwarded-For` entry rather than walking the chain, which is safe only for as long as Caddy keeps discarding client-supplied values. It does today — verified against `caddy:2.11-alpine` — but that is a default in another component, and the CIDR costs the same to write
- [x] Counters reset between tests via an autouse fixture; verified load-bearing by disabling it and watching six tests fail
- [x] **Cap the log retention.** Docker keeps container logs forever by default and these now carry real client IPs. `max-size`/`max-file` on every prod service
- [x] **Verified against a real proxy chain**, which turned out to be possible locally after all — not through `just api` (direct uvicorn, no proxy), but by running the built prod image behind a `caddy:2.11-alpine` container on a Docker network. Two persistent client containers on distinct addresses get **separate** counters (10 through, then `429`, while the second client is untouched), and a registration audits the client's address rather than Caddy's. Short-lived probe containers do *not* work as separate clients: Docker recycles the freed address, so every probe reuses one IP and the run looks exactly like the bug
- [ ] Re-check once on the deployed instance, where the client address is a real public IP rather than a Docker one
- [x] Reword the `infra-0001` gate line from *"auth rate limits kept"* to something that does not imply they already exist — the gate item is right, only the tense is wrong

## Slice 14 — Environment configuration [x]

One `.env` at the repository root, with `.env.example` as its committed twin and the only documentation of what configuration exists. The frontend keeps no env file — it had no variables, and Vite's `envDir` staying put is what makes it structurally impossible for a backend secret to reach the bundle.

`ENVIRONMENT=production` now arms a boot check: the required variables must be present and must differ from the value the example ships, Google needs a redirect URI once a client id is set, and the session cookie must be `Secure`. It exists because `secret_key` defaulted to the empty string and signs every session — a missing line failed *open*. A test asserts `Settings` and `.env.example` describe the same set, so a setting cannot ship undocumented.

**Compose truncates an env value at the first `$` and only warns**, so rotated secrets must avoid it — recorded in [setup/deployment.md](../setup/deployment.md) and on [Slice 7](#slice-7--first-deploy).

## Slice 15 — Authenticate the read endpoints

**Acceptance:** every `/api/*` route except `/api/health` and the auth surface requires an authenticated session, and a test asserts the `401` for each rather than trusting it.

Repo work, no host needed, so it runs alongside anything. **Before [Slice 10](#slice-10--security-gate-cutover-first-release)**, and ideally before the URL exists at all.

**This is not a product decision — it is the backend catching up with one already made.** [`app/routes.tsx`](../../frontend/src/app/routes.tsx) wraps dashboard, map, sessions, my-points, point detail and profile in `ProtectedRoute`; only the auth pages are public. The API disagrees: `points`, `prices`, `simulate` and `vehicles` carry no user dependency, so anyone holding the URL can pull the full ~13.7k-point catalogue, the price curve and the simulator without an account, while a real user is made to log in for exactly the same data. Publishing no ports does not help — that stops a client *bypassing* Caddy, not one arriving *through* it, and the SPA's own calls prove the path is open.

- [x] The dependency applied at the four `include_router` calls, the same shape [Slice 13](#slice-13--auth-surface-hardening) used for the limits — not sprinkled per route, where one new endpoint silently misses it. **`current_user` already existed** in `user_manager.py` and was referenced nowhere: the dependency was written and never mounted, so this slice wired up what was already there rather than adding anything
- [x] **`/api/health` stays open.** It is the container healthcheck and returns status plus version, nothing else
- [x] **The regression guard reads the route table instead of listing paths by hand**, so a router mounted unguarded fails it rather than shipping open. It has to read `app.openapi()["paths"]`: this FastAPI version keeps opaque `_IncludedRouter` entries in `app.routes` rather than the sub-routers' own routes. Verified load-bearing by unmounting one dependency and watching `GET /api/vehicles` fail
- [x] **A positive test too**, over the real credential path — register, verify, log in, then call two protected endpoints with the session cookie. The fixture overrides the dependency, so without this the suite would pass even if the gate rejected everyone
- [x] The tests in `tests/routers/` moved to an `auth_client` fixture that overrides the dependency rather than logging in per test — the real credential path is covered once, above, not sixteen times
- [x] **`just gen-api`**: the six operations now declare `security: APIKeyCookie`. Only `openapi.json` moved; `security` does not reach the generated TypeScript
- [x] Frontend needed no change. The API-level proof is the cookie round-trip above; `credentials: 'include'` is already set on the client, dev proxies `/api` through Vite so it is same-origin there too, and the PWA precaches build assets only — no API route was being served from a cache. **Not done: a browser click-through after login**, which is the one claim resting on argument rather than a run

**Worth recording when it lands:** this materially improves the position on the [REVE data rights question](../plan.md), since serving a mirrored dataset to authenticated users of one's own application is a far easier thing to defend than publishing it. It also makes rate-limiting the rest of the API moot — abuse becomes attributable to an account instead of an address, which is why [auth-0004](../decisions/auth-0004-rate-limits-and-client-ip.md) limits the auth surface and nothing else.

## Slice 16 — Pre-deploy hardening

**Acceptance:** the responses Caddy serves carry the OWASP header set minus the two entries that would break this app, the dependency audit is clean, and the weekly backup fails loudly on a host it is not configured for.

Found by auditing the repo against the [infra-0001](../decisions/infra-0001-deployment.md) gate before [Slice 7](#slice-7--first-deploy), rather than after the URL was shared.

- [x] **Security headers.** `X-Content-Type-Options`, `Referrer-Policy`, `X-Permitted-Cross-Domain-Policies`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, `Permissions-Policy`, `X-Frame-Options` and a `Content-Security-Policy` carrying **only** `frame-ancestors 'none'` — that directive takes no `default-src` fallback, so it constrains framing without waiting for the full policy. `Server` removed. **Two OWASP entries deliberately omitted**: `Cross-Origin-Embedder-Policy: require-corp` would block the OpenFreeMap tiles, which are cross-origin and send no CORP header, and `geolocation=()` would kill `useGeolocation` — it is `(self)` instead. Verified against `caddy:2.11-alpine`: all nine present on a live response
- [x] **The full CSP stays [Phase 13](../plan.md)**, unchanged: MUI and Emotion inject inline `<style>` tags and would force `style-src 'unsafe-inline'`, which is most of the value gone
- [x] **`cryptography` 49.0.0 → 50.0.0** ([CVE-2026-69247](https://advisories.gitlab.com/pypi/cryptography/CVE-2026-69247/), Bleichenbacher oracle in PKCS#7 decryption). Not reachable here — it arrives via `pyjwt[crypto]` and nothing calls `pkcs7_decrypt_*` — but a lockfile line. `pip-audit` is clean afterwards
- [x] **The interactive docs are disabled when `ENVIRONMENT=production`.** Defence in depth rather than a fix: they were **never** reachable from the internet, because Caddy forwards only `/api/*` to the backend while FastAPI mounts them at `/docs`. Confirmed by putting the prod image behind the real Caddyfile — `/docs` reaches the frontend upstream, not the API. The change closes the case where something else reaches the backend
- [x] **The weekly backup would not have run on the server.** `backup_db_cron.sh` hardcoded the development laptop's `$HOME` for both the `rclone` binary and its config; on the VPS neither path exists, and cron would have failed into a log nobody reads. Paths now derive from `$HOME`, and the script checks `rclone` and its config are present **before** dumping
- [x] **The dump is sized and its exit status kept.** The 0-byte dump that reached the offsite bucket on 2026-07-13 is [recorded in operations.md](../operations.md) as having no size check. Both halves are needed: the shell creates the file before `pg_dump` runs, so `set -e` alone leaves a plausible artifact behind — verified by pointing the script at a database that does not exist
- [x] **Recorded why only the seed dump goes offsite**, and the trigger that ends it — a wallet balance in Phase 11 makes "just register again" false, at which point the offsite copy must be a full dump encrypted client-side

**Not addressed, deliberately:** the 14-day session with no revocation ([auth-0002](../decisions/auth-0002-cookie-session.md)), the deploy key with no `command=` restriction, and the boot check verifying `SECRET_KEY` differs from the placeholder without checking it is strong. All three are known, recorded, and unchanged by this slice.

## Open decision

Whether to keep registration invite-only during the demo window. Email verification already blocks drive-by signups, so this is a judgement call rather than a gap — decide before the URL is shared.
