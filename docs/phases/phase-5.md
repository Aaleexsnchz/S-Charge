# Phase 5 — Deployment + CI/CD + releases

Per [plan.md](../plan.md): a secure, phone-accessible HTTPS instance with the refresh ETLs on an always-on server, a complete CI/CD pipeline, and semantic-version releases toward **`v1.0.0` = the build presented for evaluation**. Architecture and rejected alternatives: [infra-0001](../decisions/infra-0001-deployment.md). Host-level runbook: [setup/deployment.md](../setup/deployment.md).

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Repo-side prod artifacts | Done | #8 |
| 2 | Accounts, host, DNS | Done | host work |
| 3 | Server hardening | Done | host work |
| 4 | Toolchain: lefthook + CI hygiene | Done | #14 |
| 5 | Release plumbing: versioning, CI images, CD, `release.yml` | Done | #16 |
| 6 | Runtime versions + API contract | Not started | — |
| 7 | First deploy | Not started | host work |
| 8 | External services on the prod origin | Not started | host work |
| 9 | Close the CI/CD loop | Not started | — |
| 10 | Security gate, cutover, first release | Not started | host work |
| 11 | Renovate | Not started | — |
| 12 | REVE tariff backfill | Not started | — |
| 13 | Auth surface hardening | Not started | — |
| 14 | Environment configuration | Done | #15 |

Slices 2–14 are ordered by dependency, with two exceptions: **Slice 13 must land before [Slice 10](#slice-10--security-gate-cutover-first-release)** and **Slice 14 before [Slice 7](#slice-7--first-deploy)**, though both are numbered last because they were found after the plan was written. Each closes gaps the earlier slice depends on. **Start at 2**: the provider account and the domain are the only wall-clock-bound items (ID verification, DNS propagation), and everything on the host waits on them. **Slices 4–6 are repo work and run in parallel with that waiting** — they are independent of each other and of the host, so they can land in any order.

They are three slices rather than one because they are three unrelated review problems: hooks, release plumbing, and version bumps. Reviewing them together is what turns a PR into a rubber stamp.

**Where things stand:** **the host exists and is hardened** (Slices 2–3), but **nothing is deployed to it** — `/opt/tfm` does not exist yet and no container runs there. The app still runs only locally (`just up` + `just api`/`just web`). The REVE/PVPC refresh and DB-backup crons still run from the laptop's crontab and **have not run since early July** — see [Closing the data gap](#closing-the-data-gap); the PVPC half of that gap is already healed and baked into the seed dump. The CD workflow is **disabled** in the Actions tab because nothing is deployed for it to target — re-enabling it is Slice 9. `main` is not yet PR-protected, though changes are already going through PRs by convention.

**Next up: Slices 6 → 13**, both repo work needing no host access. After them the host chain is unblocked: Slice 5 has landed, so the first deploy will be version-stamped and its images are already proven to build in CI.

## Start here

The order to actually work in, which is not simply "slice 1 to 14".

**Step 0 — two local commands, before anything else.** No dependencies, a few minutes, and they improve what production gets bootstrapped from:

- [x] `cd backend && uv run python -m scripts.fetch_pvpc` — heals the PVPC hole from REE's history *now*, so production starts with a continuous price curve instead of one that stops in July. Nothing about this needs the server. Done: the curve is continuous from 2026-01-01 to 2026-08-01, 5111 rows, no missing hours (the only short day is 2026-03-29, the spring DST transition)
- [x] `just backup-seed` — re-take the seed dump afterwards, so [Slice 7](#slice-7--first-deploy) restores a current catalogue rather than a stale one. Done: `backups/ev_charging_seed_20260801T185624Z.dump`, verified as a valid archive carrying the nine data tables and no `users`/`oauth_account` rows

**Step 1 — start the clock (Slice 2).** Create the provider account and buy the domain *first*. Neither is work, both are waiting: ID verification can take hours and DNS has to propagate, and every host slice queues behind them.

**Step 2 — repo work while that clock runs (Slices 6 and 13 remain; [4](#slice-4--toolchain-lefthook--ci-hygiene), [14](#slice-14--environment-configuration) and [5](#slice-5--release-plumbing) are done).** Independent of the host and of each other. Order: **4** first (toolchain, because everything after is reviewed through those gates) → **14** (environment configuration, which the deploy's runbook depends on) → **5** (release plumbing, which *must* land before the first deploy so it is stamped and its images are proven to build) → **6** (runtime versions and the API contract) → **13** (auth hardening, which must land before the URL is shared).

**Step 3 — the host chain, in order:** 3 → 7 → 8 → 9 → 10, ending at `v0.1.0`. Then 11 and 12.

**Why this phase comes before the frontend migration** (Phase 6), in case it is asked again: the migration benefits from nearly every slice here — CI building the frontend prod image catches a broken build on the PR that caused it, the committed `openapi.json` stops the rewrite drifting from the API, the pre-push hook covers ~3,200 lines of churn, and CD means each migration slice lands on a URL that can be opened on a phone, which is the only way to check the one risk no tool verifies. Deployment gains nothing from the migration in return: nginx serves a `dist/` and does not care what is in it. Separately, the REVE tariff gap widens permanently every day the server does not exist.

## Decisions taken

- **Host: a 2 vCPU / 4 GB x86-64 EU VPS on Ubuntu 26.04, on Hetzner** — CX23 if in stock, else CPX22. The spec is the decision; the SKU is a purchasing detail. Fallback providers and why arm64 and GCP stay out: [infra-0001](../decisions/infra-0001-deployment.md).
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

**Acceptance:** a 2 vCPU / 4 GB x86-64 VPS running Ubuntu 26.04 in an EU region, reachable by SSH key, with the purchased domain resolving to its IP.

- [x] Provider account created and ID-verified
- [x] Server purchased on Hetzner. **Confirm before Slice 3**: 2 vCPU / 4 GB x86-64, Ubuntu 26.04 LTS, EU region, and an SSH public key attached **at creation** — if no key was attached, Hetzner mailed a root password and [Slice 3](#slice-3--server-hardening) starts from password auth instead
- [x] Domain purchased: **`s-charge.app` at Cloudflare Registrar** — the choice, the HSTS-preload consequence and the rejected `.es` are in [infra-0001](../decisions/infra-0001-deployment.md)
- [x] DNS `A` + `AAAA` records → the server's IPv4 and IPv6, both **DNS-only / grey cloud** ([deployment.md §2](../setup/deployment.md)). Verified against Cloudflare's authoritative nameservers: both resolve to the Hetzner host (rDNS `*.clients.your-server.de`) rather than a Cloudflare anycast address, so neither is proxied and Caddy can complete the ACME challenge over either protocol

## Slice 3 — Server hardening

**Acceptance:** key-only SSH on a non-root user, firewall limited to SSH + HTTP(S), Docker installed, and a dedicated deploy key authorized for CI. Commands in [setup/deployment.md](../setup/deployment.md) §1.

- [x] `deploy` user with sudo; SSH keys copied; `PermitRootLogin no` + `PasswordAuthentication no` + `KbdInteractiveAuthentication no`, set in `/etc/ssh/sshd_config.d/10-hardening.conf`. Verified from outside the host: every account answers `Permission denied (publickey)`, so `publickey` is the only method the server accepts. A root password was set first, deliberately — it is unusable over SSH and exists only for the Hetzner web console, which is the recovery path if SSH ever breaks
- [x] `ufw`: OpenSSH + 80/tcp + 443/tcp + 443/udp only, default deny incoming, rules applied to v4 and v6. Port 80 is required despite everything being HTTPS — Caddy needs it for the ACME challenge and the HTTPS redirect
- [x] `fail2ban` + `unattended-upgrades`. `unattended-upgrades` already ships enabled on the Hetzner image, both flags `1` in `20auto-upgrades`. fail2ban needs `backend = systemd` in `/etc/fail2ban/jail.local` — the default jail reads `/var/log/auth.log`, which this image does not produce, so without it fail2ban runs while banning nobody. It was already banning two probing hosts within hours of the server existing
- [x] **Understand that `ufw` does not protect Docker-published ports.** Docker writes DNAT rules that are evaluated *before* ufw's INPUT chain, so a container `ports:` entry is reachable from the internet while `ufw status` still shows a correct-looking policy. What keeps Postgres private is that `docker-compose.prod.yml` gives `db` **no `ports:` entry at all** — not the firewall. The tunnel that replaces it is now recorded in [operations.md](../operations.md) → Reaching the production database. Background: [ufw-docker](https://github.com/chaifeng/ufw-docker)
- [x] Docker Engine + Compose plugin from the official apt repo; `deploy` in the `docker` group. Docker publishes for `resolute`; the repo now uses the deb822 `.sources` format rather than the older one-line `.list`. Compose v5.3.1 as a plugin. Note the `docker` group is root-equivalent — it grants nothing new here because `deploy` already has `sudo`, which is exactly why no other user joins it
- [x] Dedicated `ed25519` deploy key generated and authorized — **not** the personal SSH key. Lives at `~/.ssh/tfm_deploy` on the laptop, no passphrase (CI cannot type one), and becomes the `DEPLOY_SSH_KEY` secret in [Slice 9](#slice-9--close-the-cicd-loop). Verified to run `docker compose` on the host with no TTY, password or `sudo` — the exact capability `cd.yml` needs. No `command=` or `from=` restriction in `authorized_keys`: CD runs arbitrary commands and GitHub's runner IPs are dynamic, so containment is that it is a separate key revocable by deleting one line

## Slice 4 — Toolchain: lefthook + CI hygiene [x]

**Acceptance:** commits and pushes are gated locally by the same checks CI runs, and secret scanning is authoritative in CI. Nothing here blocks the deploy; it lands first because everything after it is reviewed through these gates.

Measured on this machine: the whole pre-push battery runs in **8 s** wall time against ~29 s of CPU, so nothing had to be cut — the plan's fallback of dropping `pnpm build` first was not needed.

### Hooks: pre-commit → lefthook

Replaced `.pre-commit-config.yaml`. Every hook in it was a `language: system` shim with `pass_filenames: false`, so the repo paid pre-commit's Python-env bootstrap while using none of its cross-language env management, and linted the whole tree on every commit instead of the staged files. lefthook installs as a uv dev dependency, runs staged files in parallel, and can auto-fix and restage.

- [x] `lefthook.yml` **pre-commit**: ruff format + ruff check `--fix` on staged `*.py`, biome `check --write` on staged frontend files, all with `stage_fixed: true`. Two gotchas, both silent: ruff needs `--force-exclude` when paths are passed explicitly, or it lints `alembic/versions` anyway; and lefthook's default glob matcher reads `**` as *one or more* directory levels, so `frontend/**/*.json` skips `frontend/package.json` — `glob_matcher: doublestar` restores the semantics every other tool uses. `check-yaml` was dropped rather than reimplemented: GitHub rejects a malformed workflow and Compose fails on use, so broken YAML surfaces without a hook
- [x] `lefthook.yml` **pre-push** mirroring CI exactly — ruff, ruff format, basedpyright, pytest, biome, typecheck, vitest, build. Replaces "remember to run `just ci`" with something that cannot be forgotten. **Decided: pytest stays in.** The objection was that it needs Postgres, which is solvable rather than fundamental — the hook runs `docker compose up -d db` first, a no-op when it is already up. It matters because [AGENTS.md](../../AGENTS.md) forbids `--no-verify`, so a hook that omits a check leaves nothing at all stopping a bad push, and because Phase 6 is ~3,200 lines of churn where the tests are exactly what catches breakage. Run jobs in parallel so wall time is the slowest job, not the sum. **If it proves too slow, cut `pnpm build` first** — `tsc -b` in the typecheck step already covers most of it; cutting pytest is the last resort
- [x] **betterleaks moves to a CI job** scanning full history (`fetch-depth: 0`). Non-negotiable and lands in the same PR: lefthook makes the local scan best-effort, so without the CI job the repo has no secret scanning at all. There is no official action, so the job runs the published container — as the runner's uid, because git refuses to read a repository owned by someone else and the image is root. ~2 s over this history
- [x] `pre-commit` removed from the dev dependency group; hook installation folded into `just install`, and documented in [README](../../README.md) and [AGENTS.md](../../AGENTS.md). **The migration needs `pre-commit uninstall` before `lefthook install`**, or the stale shim stays in `.git/hooks` and keeps running — call it out in the PR description, since it is a manual step every clone has to repeat

### CI hygiene

Surfaced while wiring CI up; none of it blocks the deploy, all of it is cheap to fold in here.

- [x] GitHub Actions bumped off the deprecated Node 20 runtime — checkout v7, setup-node v7, pnpm/action-setup v6, setup-uv v9.0.0. **setup-uv must be pinned to a full version**: it stopped publishing floating major tags after v7 as a supply-chain measure, so `@v9` does not resolve.
- [x] pnpm aligned at 11 across CI and `frontend/Dockerfile` — CI was on 10.
- [x] uv pinned to the same version in CI and `backend/Dockerfile` — CI installed the latest uv while the image pinned 0.11.22, so `uv.lock` was resolved by a different uv than the one building the images. Bump both together.
- [x] **CI switches to `pnpm install --frozen-lockfile`.** The current `--no-frozen-lockfile` defeats lockfile integrity checking, so a green CI does not prove the lockfile is honest; `frontend/Dockerfile` already uses the frozen form. Verified locally first: the lockfile was already honest, so the flip is a no-op until it stops being
- [x] `packageManager` field in `frontend/package.json` to single-source the pnpm version instead of repeating it in `ci.yml` and the Dockerfile. `pnpm/action-setup` errors when both `packageManager` and the `version` input are set, so the input goes at the same time — and it needs `package_json_file: frontend/package.json`, since the manifest is not at the repository root. The image reads the same field through `corepack install`, replacing `npm install -g pnpm@11`. **Decided: pin the current 11.8.0, do not bump to 11.18.0** — version bumps are [Renovate's](#slice-11--renovate) job, and pinning what is already installed keeps this slice about single-sourcing rather than upgrading
- [x] `.nvmrc` + `node-version-file` in CI instead of a hardcoded Node major. It lives in `frontend/`, the only place Node is used
- [x] CI hygiene: `permissions: contents: read`, a `concurrency` group with `cancel-in-progress` on pull requests, and dependency caching for both uv and pnpm. **`cancel-in-progress` is conditioned on the event**, not left on: cancelling a superseded run on `main` would cancel the deploy it triggers

## Slice 5 — Release plumbing [x]

**Acceptance:** CI catches Dockerfile breakage, deploys stamp a version and take a database dump before migrating, and a tag push produces a GitHub Release. **This must land before the first deploy**, so that deploy is stamped and its images are already proven to build.

- [x] Version stamping: `APP_VERSION` build arg through both Dockerfiles → `/api/health` + profile screen. **It is a build argument, not runtime configuration** — Vite inlines `VITE_*` into the bundle and the backend bakes it into the image, so a deploy that forgets to export it reports `dev` until the next rebuild. Verified by building both images with a fake tag and reading it back out of the running container and the served bundle
- [x] CI job building the three prod image targets (backend `prod`, backend `scheduler`, frontend `prod`), with a GitHub Actions layer cache per target
- [x] CD hardening: `git fetch --tags` (a plain pull does not necessarily bring the tag `git describe` needs), export `APP_VERSION`, `pg_dump` before `alembic upgrade head`, keeping the last five dumps. The dump runs `pg_dump` inside the `db` container so the credentials never reach the deploy shell, and is skipped when the stack is not up yet — the first deploy has nothing to dump
- [x] `permissions: {}` on the `deploy` job in [cd.yml](../../.github/workflows/cd.yml) — it authenticates to the VPS by SSH key and never calls the GitHub API, so it should carry no `GITHUB_TOKEN` scope at all. Same hardening as the `contents: read` planned for CI in [Slice 4](#slice-4--toolchain-lefthook--ci-hygiene)
- [x] **Know the migration window, even if it stays unfixed.** `cd.yml` runs `up -d --build` and *then* `alembic upgrade head`, so the new code serves against the old schema for the seconds between them. `pg_dump`-before-migrate above improves recovery, not the window. Closing it properly means migrating before the new containers take traffic, which is a bigger change than this phase needs — at single-user demo traffic the exposure is negligible, but it should be a known trade-off rather than an oversight. Written down in [setup/deployment.md](../setup/deployment.md)
- [x] Documented rollback (`git checkout <tag>` + rebuild) in [setup/deployment.md](../setup/deployment.md), including the half git cannot undo: **code rolls back, the schema does not**, which is what the pre-migration dump is for
- [x] `release.yml`: tag push → `gh release create --generate-notes`
- [x] The AGENTS.md qualifier this item asked about no longer exists — it went in the documentation restructure before this slice started

### Image review

Both Dockerfiles were read end to end while the build arg went in. They were already close to right — multi-stage, non-root backend, no `uv` at runtime, BuildKit caches, a pinned supercronic checksum — so this is what changed, and what deliberately did not.

- [x] **The frontend image had no `HEALTHCHECK`** while the backend had one. Added — and it failed on the first run: `localhost` resolves to `::1` first, nginx listens on IPv4 only, and busybox `wget` does not fall back the way Python's `urllib` does, which is why the backend's equivalent check never exposed the same asymmetry. Pointed at `127.0.0.1`; both containers verified reaching `healthy`
- [x] **`python:3.12-slim` appeared in two `FROM` lines**, so [Slice 6](#slice-6--runtime-versions--api-contract)'s bump to 3.13 would have been two edits with one easy to miss. Single-sourced to an `ARG PYTHON_VERSION`
- **Base images stay on floating tags** (`python:3.12-slim`, `nginx:1.27-alpine`, `caddy:2.11-alpine`, `postgres:18-alpine`). Digest pinning is the reproducibility upgrade, but pinning by hand now means stale digests until something maintains them; it belongs with [Renovate](#slice-11--renovate), which raises digest updates as pull requests
- **nginx still runs its master process as root.** The unprivileged image would fix that, but it listens on 8080, so it is a `Caddyfile` and compose change too — worth doing, not worth bundling into a release-plumbing slice. Backend and scheduler already run as `appuser`
- Sizes for the record: backend `prod` 330 MB, `scheduler` 356 MB, frontend `prod` 77.5 MB

## Slice 6 — Runtime versions + API contract

**Acceptance:** CI and production run the versions the project has settled on, and a backend contract change breaks CI instead of the frontend at runtime. Independent of the host work; the dev-database cutover is the only part that is not on the deploy path at all.

- [ ] **Postgres 18 for CI and production** — tags already bumped in `docker-compose.prod.yml` and `ci.yml`. Production is provisioned fresh on 18, so it never performs a major upgrade; it restores a seed dump into an empty cluster. Rehearsed on 2026-08-01: a PG17 `pg_dump -Fc` restored into 18.4 with zero errors, identical row counts, `alembic current` at head, 104 tests green and the API serving from it
- [ ] **Cut the dev database over to 18** — `docker-compose.yml` is deliberately still on `17-alpine` because the local volume holds the ~12-day REVE seed and the data directory is not compatible across majors. Dump, `down -v`, flip the tag, restore ([operations.md](../operations.md)). Until this is done, dev runs 17 while CI and production run 18
- [ ] **Python 3.12 → 3.13**: `requires-python`, both `Dockerfile` stages, ruff `target-version`, basedpyright `pythonVersion`, CI `python-version`. Verified: the full dependency set resolves, installs and imports on 3.13/3.14 (asyncpg's C extension included). **3.13, not 3.14** — it is the version the agent/LLM SDK ecosystem targets, and Phase 11 depends on that ecosystem
- [ ] **Committed `openapi.json`**: a console script exports it from the app, the file is committed, `pnpm run gen:api` reads the file instead of a running backend, and CI regenerates and fails on a diff — so a backend contract change breaks CI rather than the frontend at runtime

## Slice 7 — First deploy

**Acceptance:** the app loads over HTTPS on a phone, the PWA installs, `/api/health` reports ok with a version, and the scheduler container runs both ETL jobs. Full detail in [setup/deployment.md](../setup/deployment.md) §3–5.

- [ ] Repo cloned to `/opt/tfm` (the path `cd.yml` assumes)
- [ ] The server-side `.env` written with **every secret rotated** — fresh `SECRET_KEY`, new `POSTGRES_PASSWORD`, `ENVIRONMENT=production`, `APP_DEBUG=false`, `SESSION_COOKIE_SECURE=true`, empty `CORS_ALLOW_ORIGINS`, prod `APP_BASE_URL` / `GOOGLE_REDIRECT_URI`, `SITE_ADDRESS`; copies kept in a password manager, and **no value containing `$`** ([Slice 14](#slice-14--environment-configuration)). `ENVIRONMENT=production` arms the boot check, so a misconfigured file now restart-loops the backend instead of serving with a development secret
- [ ] Database bootstrapped from the latest seed dump — **never re-seed**, the REVE catalogue takes ~12 days under the 5 req/hr cap
- [ ] `up -d --build` + `alembic upgrade head`
- [ ] Verified: site on a phone, PWA installs, `/api/health` returns the version, `logs scheduler` shows supercronic loading both jobs

### Closing the data gap

The ETLs stopped when the laptop did. The PVPC hole is closed; the REVE one is measured as of 2026-08-01 and keeps growing until the scheduler runs on the server.

- [x] **PVPC prices — recoverable, backfilled.** The hole ran from **2026-07-03** to 2026-08-01, 29 days. `fetch_pvpc.py` gap-backfills from the last stored hour to tomorrow and REE serves history, so it healed completely in one local run ([Step 0](#start-here)) — production is bootstrapped from a seed dump that already contains the full curve. The daily tick keeps it current from there
- [ ] **REVE tariffs — recover what REVE will still serve, then accept the rest.** The refresh watermark is stuck at **2026-07-08 19:30** behind a 504. How much of that stretch is recoverable is an empirical question about REVE, not a decision to take here: it is [Slice 12](#slice-12--reve-tariff-backfill), which runs after the deploy because it needs the scheduler's environment and a working cron. **The ordering constraint is here:** the watermark has not been jumped yet — the 504 hit while it was still recent, so it was classed transient and left in place — and the first unattended refresh tick *will* jump it to `now − REVE_REFRESH_LOOKBACK_HOURS`. Read `--status` before enabling the scheduler and note the value, so Slice 12 knows where to probe from
- [x] **Re-take the seed dump immediately before bootstrapping the server**, after the PVPC backfill, so production starts from the freshest catalogue. Done in [Step 0](#start-here); re-take again if the deploy slips far enough that the dump goes stale
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

- [ ] `/security-review` run; infra-0001 gate passed (HSTS, only 22/80/443 open, no published `5432`, secrets rotated, cookie `Secure`, CORS empty, backup restorable, auth endpoints rate-limited and logging the real client IP per [Slice 13](#slice-13--auth-surface-hardening))
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

## Slice 12 — REVE tariff backfill

**Acceptance:** the tariff watermark has been advanced from 2026-07-08 by the largest span REVE will actually serve, the unrecoverable remainder is measured rather than assumed, and both numbers are written into [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).

Last, because it needs the scheduler's environment, a working cron and a budget that is not competing with the deploy. It is also the only slice whose outcome is not under the project's control.

**The constraint.** `/connectors/tariffs` takes `date_from` and no `date_to`, so a stale range cannot be sliced into chunks — the only lever is *how far back `date_from` points*. A wide window makes REVE scan too much and time out; a narrow one returns quickly but recovers less history. There is therefore no way to backfill the gap in pieces, and the whole slice reduces to one measurement: **the oldest `date_from` REVE will answer with a 200.** Everything older than that is unrecoverable through this endpoint at any price.

Note that the gap is **self-healing per connector, but only forward**: any connector whose tariff changes after the deploy re-emits its current price on the next tick. What is lost is the intermediate history of connectors that changed during the gap and then went quiet — the stored price is stale until that connector next moves.

The production database inherits the stuck watermark from the seed dump (`reve_etl_cursor` is in the archive), so the probe runs against the same starting point locally and on the server.

**Expect to recover almost none of it.** The ceiling was already measured once under controlled conditions ([precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md)): `date_from` at ~100 h, ~20 h and intermediate values all returned 504, while `now − 3 h` returned 200. The servable window is **hours wide**, so a ~24-day gap is written off almost in full unless REVE's performance has changed since. This slice exists to turn "almost in full" into a number, not to rescue the data.

- [ ] **Stop the scheduler before probing by hand.** Every probe below is a second writer against `reve_etl_cursor` while the hourly cron ticks, and two concurrent runs corrupt the watermark — the field whose loss caused this gap in the first place. `docker compose -f docker-compose.prod.yml stop scheduler` for the duration, and start it again after. The permanent fix is an advisory lock, deferred to Phase 12 ([production-readiness.md](../production-readiness.md)); until it lands, this is a manual discipline
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

- [ ] **Rate-limit the auth endpoints.** `slowapi` is declared in `backend/pyproject.toml` and imported nowhere in `app/`: login, register and password-reset accept unlimited attempts. Email verification blocks drive-by *registration*, but does nothing about attempts against accounts that already exist, and password-reset is an unmetered send-an-email endpoint for anyone who finds it. Wire the limiter and cover at least `/api/auth/login`, registration, and the reset request
- [ ] **Trust Caddy's forwarded headers.** `backend/app/services/user_manager.py` logs `request.client.host` on four auth events, but uvicorn's `--forwarded-allow-ips` defaults to `127.0.0.1` and Caddy connects from a Docker network address — so every event will record Caddy's container IP. Add `--forwarded-allow-ips="*"` to the `prod` stage `CMD` in [backend/Dockerfile](../../backend/Dockerfile). The wildcard is safe **only** because `backend` publishes no ports and Caddy is the sole thing that can reach it; it would be a header-spoofing hole on a directly-exposed backend
- [ ] **Order matters between the two.** Fixing the limiter without the proxy headers produces a limiter that sees one client and throttles every user at once. Land the header fix first, or both together
- [ ] **Verify on the deployed instance, not locally**: log in once and confirm the audit line carries your own IP, then exceed the limit and confirm a `429`. Neither can be verified through a local direct-to-uvicorn request, because the bug only exists behind the proxy
- [ ] Reword the `infra-0001` gate line from *"auth rate limits kept"* to something that does not imply they already exist — the gate item is right, only the tense is wrong

## Slice 14 — Environment configuration [x]

**Acceptance:** one env file at the repository root, one object that reads it, and a production boot that refuses to start on a missing required secret instead of running with an empty one.

**It must land before [Slice 7](#slice-7--first-deploy)**, which writes the server-side env files and owns the runbook that describes them. Afterwards the same change costs a runbook rewrite plus an edit on a live server.

### The scheme

**One file, one reader, three tiers.** The root `.env` is the only env file; `.env.example` is its committed twin and *is* the documentation — there is no second list of "what you need to set". Real environment variables still win over the file, which is how CI injects an ephemeral `SECRET_KEY` and how CD could inject anything with no file at all.

The tier decides the default:

| Tier | Default | Missing in production means |
| --- | --- | --- |
| **Required in prod** — `SECRET_KEY`, `DATABASE_URL`, `APP_BASE_URL`, `GOOGLE_REDIRECT_URI` | none | boot fails, loudly |
| **Tuned** — token lifetime, API base URLs, REVE budget and lookback | a working dev value | runs on the default, which is fine |
| **Optional integration** — `RESEND_*`, `GOOGLE_*` credentials | empty | the feature is off, which is already the design |

### Why it is worth a slice

**`secret_key` defaults to `""` and that value signs sessions.** It is the secret behind the session JWT (`utils/auth_backend.py`), the password-reset token and the verification token (`services/user_manager.py`). A server whose `.env` is missing, misnamed, or merely missing that one line **boots normally and signs sessions with an empty secret** — forgeable session cookies and password-reset tokens for any account, with no warning anywhere. It fails *open*. Slice 7 says "fresh `SECRET_KEY`" and [Slice 10](#slice-10--security-gate-cutover-first-release)'s gate says "secrets rotated", but nothing enforces either; both are a human remembering.

**Three variables bypass `Settings` entirely** — `REVE_BUDGET_PER_RUN` and `REVE_REFRESH_LOOKBACK_HOURS`, read with `os.getenv` in `scripts/refresh_reve.py` and `scripts/seed_reve.py`. None appears in `.env.example`, so on the server they are invisible, and [Slice 12](#slice-12--reve-tariff-backfill) plans to retune the lookback once the servable window is measured — which today means editing a literal and rebuilding the image.

- [x] **Single root `.env` + `.env.example`**, merging `backend/.env.example` and the one-variable root file. `frontend/.env` and `frontend/.env.example` are **deleted**: they contain no variables at all, only comments, and `VITE_PROXY_TARGET` in `vite.config.ts` reads `process.env` — the shell, never that file
- [x] **Vite's `envDir` stays `frontend/`.** Today it is structurally impossible for a backend secret to reach the JS bundle, because the directory Vite reads env from holds none. Pointing it at the root would trade that away for one file: a `VITE_`-prefixed typo, or `loadEnv(mode, dir, '')` with an empty prefix, would ship `SECRET_KEY` and `REVE_API_KEY` to the browser. If a real `VITE_*` var ever appears it gets its own `frontend/.env`
- [x] `config.py` `env_file` → repository root. Inside the prod image that path resolves to a missing `/.env`, which pydantic ignores — production gets real environment variables through compose's `env_file:` anyway
- [x] **Production validator**: when `ENVIRONMENT=production`, the tier-1 variables must be present and must not still hold their development default. This finally gives the `environment` setting the job its TODO has been waiting for
- [x] `REVE_BUDGET_PER_RUN` and `REVE_REFRESH_LOOKBACK_HOURS` become `Settings` fields, documented in `.env.example`
- [x] **A test asserting `Settings.model_fields` and the keys in `.env.example` are the same set.** Ten lines, and it permanently kills the "added a setting, forgot the server" failure — the one that costs an evening during a deploy rather than a minute at a desk
- [x] Both compose files read `./.env`; the justfile's `SITE_ADDRESS=${SITE_ADDRESS:-localhost}` prefix disappears, since compose auto-loads the root `.env` for interpolation — which is what that hack was working around
- [x] `test_database_url` still defaults to `@db:5432`, left from when dev ran in containers, and disagrees with `.env.example`
- [x] Docs: [README](../../README.md) quick start (one `cp`, not three), [operations.md](../operations.md), [setup/deployment.md](../setup/deployment.md), [setup/google-oauth.md](../setup/google-oauth.md), [setup/email.md](../setup/email.md)

**Generate the rotated secrets `$`-free.** Compose truncates an env value at the first `$` and only warns — `PASS=ab$cd$ef` reaches the container as `ab`, with a "the cd variable is not set" line nobody reads. This is **not** new to the root file; it applies to `env_file:` at any path, so it is already true today. What makes it dangerous is that the native backend reads the file directly and gets the full value while every container gets the truncated one: dev and prod disagreeing on a password, surfacing as an authentication failure during the first deploy. `openssl rand -hex 32` is safe; a password manager's "special characters" toggle is not.

**Noted, not fixed here:** the `db` container's `env_file` hands Postgres `RESEND_API_KEY`, `REVE_API_KEY` and `SECRET_KEY`, which it has no use for — anything with `docker exec` on `db` reads them. Splitting the `POSTGRES_*` variables into their own file would fix it. Unchanged by this slice, which only makes it easier to see.

## Open decision

Whether to keep registration invite-only during the demo window. Email verification already blocks drive-by signups, so this is a judgement call rather than a gap — decide before the URL is shared.
