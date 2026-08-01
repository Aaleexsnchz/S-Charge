# Phase 5 — Deployment + CI/CD + releases

Per [plan.md](../plan.md): a secure, phone-accessible HTTPS instance with the refresh ETLs on an always-on server, a complete CI/CD pipeline, and semantic-version releases toward **`v1.0.0` = the build presented for evaluation**. Architecture and rejected alternatives: [infra-0001](../decisions/infra-0001-deployment.md). Host-level runbook: [setup/deployment.md](../setup/deployment.md).

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Repo-side prod artifacts | Done | #8 |
| 2 | Accounts, host, DNS | Not started | host work |
| 3 | Server hardening | Not started | host work |
| 4 | Toolchain: lefthook + CI hygiene | Not started | — |
| 5 | Release plumbing: versioning, CI images, CD, `release.yml` | Not started | — |
| 6 | Runtime versions + API contract | Not started | — |
| 7 | First deploy | Not started | host work |
| 8 | External services on the prod origin | Not started | host work |
| 9 | Close the CI/CD loop | Not started | — |
| 10 | Security gate, cutover, first release | Not started | host work |
| 11 | Renovate | Not started | — |

Slices 2–11 are ordered by dependency. **Start at 2**: the provider account and the domain are the only wall-clock-bound items (ID verification, DNS propagation), and everything on the host waits on them. **Slices 4–6 are repo work and run in parallel with that waiting** — they are independent of each other and of the host, so they can land in any order.

They are three slices rather than one because they are three unrelated review problems: hooks, release plumbing, and version bumps. Reviewing them together is what turns a PR into a rubber stamp.

**Where things stand:** nothing is deployed. The app runs locally (`just up` + `just api`/`just web`); the REVE/PVPC refresh and DB-backup crons still run from the laptop's crontab and **have not run since early July** — see [Closing the data gap](#closing-the-data-gap). The CD workflow is **disabled** in the Actions tab because there is no server to target — re-enabling it is Slice 9. `main` is not yet PR-protected.

## Start here

The order to actually work in, which is not simply "slice 1 to 11".

**Step 0 — two local commands, before anything else.** No dependencies, a few minutes, and they improve what production gets bootstrapped from:

- [ ] `cd backend && uv run python -m scripts.fetch_pvpc` — heals the PVPC hole from REE's history *now*, so production starts with a continuous price curve instead of one that stops in July. Nothing about this needs the server
- [ ] `just backup-seed` — re-take the seed dump afterwards. The newest is from 2026-07-08 and [Slice 7](#slice-7--first-deploy) restores it into production; taking it after the backfill saves a round trip

**Step 1 — start the clock (Slice 2).** Create the provider account and buy the domain *first*. Neither is work, both are waiting: ID verification can take hours and DNS has to propagate, and every host slice queues behind them.

**Step 2 — repo work while that clock runs (Slices 4, 5, 6).** Independent of the host and of each other. Suggested order: **4** (toolchain, because everything after is reviewed through those gates) → **5** (release plumbing, which *must* land before the first deploy so it is stamped and its images are proven to build) → **6** (runtime versions and the API contract).

**Step 3 — the host chain, in order:** 3 → 7 → 8 → 9 → 10, ending at `v0.1.0`. Then 11.

**Why this phase comes before the frontend migration** (Phase 6), in case it is asked again: the migration benefits from nearly every slice here — CI building the frontend prod image catches a broken build on the PR that caused it, the committed `openapi.json` stops the rewrite drifting from the API, the pre-push hook covers ~3,200 lines of churn, and CD means each migration slice lands on a URL that can be opened on a phone, which is the only way to check the one risk no tool verifies. Deployment gains nothing from the migration in return: nginx serves a `dist/` and does not care what is in it. Separately, the REVE tariff gap widens permanently every day the server does not exist.

## Decisions taken

- **Host: a 2 vCPU / 4 GB x86-64 EU VPS on Ubuntu 24.04, on Hetzner** — CX23 if in stock, else CPX22. The spec is the decision; the SKU is a purchasing detail. Fallback providers and why arm64 and GCP stay out: [infra-0001](../decisions/infra-0001-deployment.md).
- **A real registered domain** (~€10/yr) over a free DuckDNS subdomain. `duckdns.org` sits on the Public Suffix List, so Google treats the subdomain as the top private domain and wants it verified before accepting it as an OAuth authorised domain. A registrable domain removes that friction and reads better at the defense.
- **Prod images build in CI**, not only on the VPS. As built, a change that breaks either Dockerfile passes CI green and fails on the server at deploy time.
- **Releases are tagged manually**, version derived from the tag — [infra-0002](../decisions/infra-0002-manual-release-tagging.md).

## Release policy

Recorded permanently in [infra-0002](../decisions/infra-0002-manual-release-tagging.md): manual tags, version derived from `git describe`, no changelog file, and why `release-please` was evaluated and reversed. This phase only *implements* it — `release.yml` and the version stamping are [Slice 5](#slice-5--release-plumbing).

## Slice 1 — Repo-side prod artifacts [x]

**Acceptance:** the production stack builds and runs locally with TLS, an in-container scheduler and no published Postgres port.

- [x] `docker-compose.prod.yml` as a standalone file (not an override) + `Caddyfile`
- [x] `scheduler` image stage (supercronic + repo-committed `backend/crontab`) replacing the host refresh crons
- [x] `cd.yml` triggered by a successful CI run on `main`
- [x] Env-driven CORS; root `justfile`; provisioning runbook in [setup/deployment.md](../setup/deployment.md)

## Slice 2 — Accounts, host, DNS

**Acceptance:** a 2 vCPU / 4 GB x86-64 VPS running Ubuntu 24.04 in an EU region, reachable by SSH key, with the purchased domain resolving to its IP.

- [ ] Plan chosen: Hetzner CX23 if in stock (check FSN/NBG/HEL separately), else CPX22 — spec and fallbacks in [infra-0001](../decisions/infra-0001-deployment.md)
- [ ] Provider account created — **start here**, new accounts may need ID verification (hours)
- [ ] Domain purchased (~€10/yr; `.es`, `.app` and `.dev` all fine)
- [ ] Server created: Ubuntu 24.04 LTS, EU region, SSH public key attached **at creation**
- [ ] DNS A record → server IPv4 (AAAA → IPv6 if enabled); Caddy cannot obtain a certificate until this resolves

## Slice 3 — Server hardening

**Acceptance:** key-only SSH on a non-root user, firewall limited to SSH + HTTP(S), Docker installed, and a dedicated deploy key authorized for CI. Commands in [setup/deployment.md](../setup/deployment.md) §1.

- [ ] `deploy` user with sudo; SSH keys copied; `PermitRootLogin no` + `PasswordAuthentication no`
- [ ] `ufw`: OpenSSH + 80/tcp + 443/tcp + 443/udp only; `fail2ban` + `unattended-upgrades`
- [ ] Docker Engine + Compose plugin from the official apt repo; `deploy` in the `docker` group
- [ ] Dedicated `ed25519` deploy key generated and authorized — **not** the personal SSH key

## Slice 4 — Toolchain: lefthook + CI hygiene

**Acceptance:** commits and pushes are gated locally by the same checks CI runs, and secret scanning is authoritative in CI. Nothing here blocks the deploy; it lands first because everything after it is reviewed through these gates.

### Hooks: pre-commit → lefthook

Replaces [.pre-commit-config.yaml](../../.pre-commit-config.yaml). Every current hook is a `language: system` shim with `pass_filenames: false`, so the repo pays pre-commit's Python-env bootstrap while using none of its cross-language env management, and lints the whole tree on every commit instead of the staged files. lefthook installs as a uv dev dependency, runs staged files in parallel, and can auto-fix and restage.

- [ ] `lefthook.yml` **pre-commit**: ruff format + ruff check `--fix` on staged `*.py`, biome `check --write` on staged frontend files, all with `stage_fixed: true`
- [ ] `lefthook.yml` **pre-push** mirroring CI exactly — ruff, ruff format, basedpyright, pytest, biome, typecheck, vitest, build. Replaces "remember to run `just ci`" with something that cannot be forgotten
- [ ] **betterleaks moves to a CI job** scanning full history (`fetch-depth: 0`). Non-negotiable and lands in the same PR: lefthook makes the local scan best-effort, so without the CI job the repo has no secret scanning at all
- [ ] `pre-commit` removed from the dev dependency group; `lefthook install` documented in [README](../../README.md) and [AGENTS.md](../../AGENTS.md)

### CI hygiene

Surfaced while wiring CI up; none of it blocks the deploy, all of it is cheap to fold in here.

- [x] GitHub Actions bumped off the deprecated Node 20 runtime — checkout v7, setup-node v7, pnpm/action-setup v6, setup-uv v9.0.0. **setup-uv must be pinned to a full version**: it stopped publishing floating major tags after v7 as a supply-chain measure, so `@v9` does not resolve.
- [x] pnpm aligned at 11 across CI and `frontend/Dockerfile` — CI was on 10.
- [x] uv pinned to the same version in CI and `backend/Dockerfile` — CI installed the latest uv while the image pinned 0.11.22, so `uv.lock` was resolved by a different uv than the one building the images. Bump both together.
- [ ] **CI switches to `pnpm install --frozen-lockfile`.** The current `--no-frozen-lockfile` defeats lockfile integrity checking, so a green CI does not prove the lockfile is honest; `frontend/Dockerfile` already uses the frozen form. Flipping it breaks CI if the lockfile is genuinely out of sync — verify locally first.
- [ ] `packageManager` field in `frontend/package.json` to single-source the pnpm version instead of repeating it in `ci.yml` and the Dockerfile. `pnpm/action-setup` errors when both `packageManager` and the `version` input are set, so the input goes at the same time.
- [ ] `.nvmrc` + `node-version-file` in CI instead of a hardcoded Node major.
- [ ] CI hygiene: `permissions: contents: read`, a `concurrency` group with `cancel-in-progress` on pull requests, and dependency caching for both uv and pnpm.

## Slice 5 — Release plumbing

**Acceptance:** CI catches Dockerfile breakage, deploys stamp a version and take a database dump before migrating, and a tag push produces a GitHub Release. **This must land before the first deploy**, so that deploy is stamped and its images are already proven to build.

- [ ] Version stamping: `APP_VERSION` build arg through both Dockerfiles → `/api/health` + profile screen
- [ ] CI job building the three prod image targets (backend `prod`, backend `scheduler`, frontend `prod`)
- [ ] CD hardening: `git fetch --tags`, export `APP_VERSION`, `pg_dump` before `alembic upgrade head`
- [ ] Documented rollback (`git checkout <tag>` + rebuild) in [setup/deployment.md](../setup/deployment.md)
- [ ] `release.yml`: tag push → `gh release create --generate-notes`
- [ ] Drop the "lands with Phase 5 Slice 5" qualifier in [AGENTS.md](../../AGENTS.md) once `release.yml` exists, and make it a link

## Slice 6 — Runtime versions + API contract

**Acceptance:** CI and production run the versions the project has settled on, and a backend contract change breaks CI instead of the frontend at runtime. Independent of the host work; the dev-database cutover is the only part that is not on the deploy path at all.

- [ ] **Postgres 18 for CI and production** — tags already bumped in `docker-compose.prod.yml` and `ci.yml`. Production is provisioned fresh on 18, so it never performs a major upgrade; it restores a seed dump into an empty cluster. Rehearsed on 2026-08-01: a PG17 `pg_dump -Fc` restored into 18.4 with zero errors, identical row counts, `alembic current` at head, 104 tests green and the API serving from it
- [ ] **Cut the dev database over to 18** — `docker-compose.yml` is deliberately still on `17-alpine` because the local volume holds the ~12-day REVE seed and the data directory is not compatible across majors. Dump, `down -v`, flip the tag, restore ([operations.md](../operations.md)). Until this is done, dev runs 17 while CI and production run 18
- [ ] **Python 3.12 → 3.13**: `requires-python`, both `Dockerfile` stages, ruff `target-version`, basedpyright `pythonVersion`, CI `python-version`. Verified: the full dependency set resolves, installs and imports on 3.13/3.14 (asyncpg's C extension included). **3.13, not 3.14** — it is the version the agent/LLM SDK ecosystem targets, and Phase 11 depends on that ecosystem
- [ ] **Committed `openapi.json`**: a console script exports it from the app, the file is committed, `pnpm run gen:api` reads the file instead of a running backend, and CI regenerates and fails on a diff — so a backend contract change breaks CI rather than the frontend at runtime

## Slice 7 — First deploy

**Acceptance:** the app loads over HTTPS on a phone, the PWA installs, `/api/health` reports ok with a version, and the scheduler container runs both ETL jobs. Full detail in [setup/deployment.md](../setup/deployment.md) §3–5.

- [ ] Repo cloned to `/opt/tfm` (the path `cd.yml` assumes)
- [ ] Server-side `.env` files written with **every secret rotated** — fresh `SECRET_KEY`, new `POSTGRES_PASSWORD`, `ENVIRONMENT=production`, `APP_DEBUG=false`, `SESSION_COOKIE_SECURE=true`, empty `CORS_ALLOW_ORIGINS`, prod `APP_BASE_URL` / `GOOGLE_REDIRECT_URI`; copies kept in a password manager
- [ ] Database bootstrapped from the latest seed dump — **never re-seed**, the REVE catalogue takes ~12 days under the 5 req/hr cap
- [ ] `up -d --build` + `alembic upgrade head`
- [ ] Verified: site on a phone, PWA installs, `/api/health` returns the version, `logs scheduler` shows supercronic loading both jobs

### Closing the data gap

The ETLs stopped when the laptop did. Both gaps are measured as of 2026-08-01; re-measure at deploy time, because both keep growing.

- [ ] **PVPC prices — recoverable, backfill them.** Last stored hour is **2026-07-03**, a 29-day hole. `fetch_pvpc.py` gap-backfills from the last stored hour to tomorrow and REE serves history, so this heals completely: run it explicitly after the first deploy instead of waiting for the daily tick, then verify the curve is continuous from 2026-07-03 to today. Any PVPC-priced simulation and the optimiser are wrong until this is done
- [ ] **REVE tariffs — decide, because part of this gap is not recoverable.** The refresh watermark is stuck at **2026-07-08 19:30** after a 504 (the documented REVE-side regression on wide windows). On resume the script sees a stale watermark, **jumps it to `now − REVE_REFRESH_LOOKBACK_HOURS`** and audits `reve_refresh_jumped_to_recent` — so tariff changes between 2026-07-08 and the deploy date are **skipped permanently**, not backfilled. Options: accept the gap and state it in the thesis (prices are a snapshot with a documented hole), or force a wider re-pull, which costs days under the 5 req/hr cap. Accepting is the default, but the choice should be deliberate
- [ ] **Re-take the seed dump immediately before bootstrapping the server**, after the PVPC backfill, so production starts from the freshest catalogue rather than the 2026-07-08 artifact
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
- [ ] CD workflow re-enabled in the Actions tab
- [ ] Branch protection ruleset on `main`: **require a pull request**, require the CI checks, block force-push and deletion
- [ ] **End-to-end test:** trivial PR → merge → CI green → CD deploys → the version string in production changes. The only proof the pipeline works.

## Slice 10 — Security gate, cutover, first release

**Acceptance:** the infra-0001 pre-deploy gate passes, the laptop is no longer part of production, and `v0.1.0` is tagged.

- [ ] `/security-review` run; infra-0001 gate passed (HSTS, only 22/80/443 open, no published `5432`, secrets rotated, cookie `Secure`, CORS empty, backup restorable)
- [ ] Laptop crontab refresh/PVPC lines removed — the scheduler container owns them now
- [ ] `backup_db_cron.sh` moved to the server crontab (needs `rclone` + B2 config on the VPS; its hardcoded paths adjusted)
- [ ] **`v0.1.0` tagged**
- [ ] infra-0001 flipped to `accepted`; B2 lifecycle rule added on `tfm-db-backups`

## Slice 11 — Renovate

**Acceptance:** Renovate opens grouped dependency PRs on a weekly schedule, and they are gated by the same CI as any other PR.

Lands **after** Slice 9, so the first automated PRs arrive against a pipeline that is already proven end to end. The Phase 5 toolchain-hygiene list above — deprecated Node runtime, pnpm 10 vs 11 drift, uv pinned differently in CI and the Dockerfile — is a list of things Renovate would have raised as PRs instead of being found by hand.

- [ ] Renovate GitHub App installed on the repository
- [ ] `renovate.json`: weekly schedule, non-majors grouped into one PR, dev dependencies grouped, majors one at a time, dependency dashboard, `:semanticCommits` so PR titles match the Conventional Commits rule
- [ ] Scope includes `github-actions` and the Docker base images, not just `uv`/`pnpm` manifests
- [ ] `vulnerabilityAlerts` unscheduled, so security updates are not held for the weekly window
- [ ] No automerge — every dependency PR merges by hand, because merging to `main` deploys to production

## Open decision

Whether to keep registration invite-only during the demo window. Email verification already blocks drive-by signups, so this is a judgement call rather than a gap — decide before the URL is shared.
