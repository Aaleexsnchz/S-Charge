# Phase 6 — Deployment + CI/CD + releases

Per [PLAN.md](../PLAN.md): a secure, phone-accessible HTTPS instance with the refresh ETLs on an always-on server, a complete CI/CD pipeline, and semantic-version releases toward **`v1.0.0` = the build presented for evaluation**. Architecture and rejected alternatives: [infra-0001](../decisions/infra-0001-deployment.md). Host-level runbook: [setup/deployment.md](../setup/deployment.md).

**Slice A is already done** — the repo-side artifacts shipped in PR #8 (2026-07-08): `docker-compose.prod.yml`, `Caddyfile`, the `scheduler` image stage, `cd.yml`, env-driven CORS. Everything below is what remains.

Slices B–H are ordered by dependency. B and C have external latency (account verification, DNS propagation) and gate everything else, so they start first; D runs in parallel with them.

## Decisions taken (2026-07-27)

Four choices were open at the start of this phase and are now fixed:

- **Host: Hetzner CX22.** Confirms the infra-0001 default over the Oracle Always-Free fallback (which would need an arm64 supercronic binary and arm64 image rebuilds first). GCP was reconsidered and rejected: its Always-Free tier is a 1 GB `e2-micro` in US-only regions — too small to build images on and it forfeits the EU data-locality argument — and the free trial has expired, so anything larger bills at ~3x Hetzner.
- **A real registered domain** (~€10/yr) over a free DuckDNS subdomain. `duckdns.org` sits on the Public Suffix List, so Google treats the subdomain as the top private domain and wants it verified before accepting it as an OAuth authorised domain. A registrable domain removes that friction and reads better at the defense.
- **Prod images build in CI**, not only on the VPS. Today a change that breaks either Dockerfile passes CI green and fails on the server at deploy time.
- **Releases are tagged manually** — see [Release policy](#release-policy). `release-please` was evaluated and rejected.

## Release policy

Recorded here and in [AGENTS.md](../../AGENTS.md); this section is the rationale, AGENTS.md is the operating rule.

**Versions are chosen deliberately, not derived from commit types.** A minor bump marks a phase or a meaningful feature set shipping; a patch marks fixes on top. `v0.1.0` is the first successful production deploy — release history starts at deployment, not retroactively at Phase 1. **`v1.0.0` is the build presented for the thesis.**

**The running version comes from the git tag, not from a file.** `git describe --tags` at image build time feeds an `APP_VERSION` build arg, surfaced in `/api/health` and on the profile screen. Between tags it reads `v0.1.0-3-gabc1234`, so production always states how far ahead of the last release it is. Nothing has to be kept in sync by hand.

**Why not `release-please`.** It was the initial pick and was reversed after reading its config model. It derives the bump from commit types, which fights a thesis narrative where the version should say "this is Phase 7" — steering it means `Release-As:` footers on commits, more ceremony than tagging by hand. Its main value is keeping version strings in `pyproject.toml` / `package.json` / the UI in sync, a problem that disappears entirely when the version is derived from the tag. Against that it wants a repo setting allowing Actions to open PRs, adds a bot-authored PR per release, and PRs it opens with `GITHUB_TOKEN` do not trigger CI — so release PRs would be the only unchecked ones. At ~10–20 releases over this project's life the automation never pays for itself. `semantic-release` (tags on every push, no gate) and `changesets` (built for publishing JS packages) fit worse still.

**Future option:** [git-cliff](https://git-cliff.org) generates a `CHANGELOG.md` from the existing Conventional Commits on demand, with no bot and no PRs — the thing to reach for if the thesis wants a changelog appendix. Parked in [ideas-backlog.md](../ideas-backlog.md).

## Slice B — Accounts, host, DNS

**Acceptance:** a CX22 running Ubuntu 24.04 in an EU region, reachable by SSH key, with the purchased domain resolving to its IP.

- [ ] Hetzner account created — **start here**, new accounts may need ID verification (hours)
- [ ] Domain purchased (~€10/yr; `.es`, `.app` and `.dev` all fine)
- [ ] CX22 created: Ubuntu 24.04 LTS, EU region, SSH public key attached **at creation**
- [ ] DNS A record → server IPv4 (AAAA → IPv6 if enabled); Caddy cannot obtain a certificate until this resolves

## Slice C — Server hardening

**Acceptance:** key-only SSH on a non-root user, firewall limited to SSH + HTTP(S), Docker installed, and a dedicated deploy key authorized for CI. Commands in [setup/deployment.md](../setup/deployment.md) §1.

- [ ] `deploy` user with sudo; SSH keys copied; `PermitRootLogin no` + `PasswordAuthentication no`
- [ ] `ufw`: OpenSSH + 80/tcp + 443/tcp + 443/udp only; `fail2ban` + `unattended-upgrades`
- [ ] Docker Engine + Compose plugin from the official apt repo; `deploy` in the `docker` group
- [ ] Dedicated `ed25519` deploy key generated and authorized — **not** the personal SSH key

## Slice D — Repo work (parallel with B and C)

**Acceptance:** CI catches Dockerfile breakage, deploys stamp a version and take a database dump before migrating, and a tag push produces a GitHub Release.

- [ ] Version stamping: `APP_VERSION` build arg through both Dockerfiles → `/api/health` + profile screen
- [ ] CI job building the three prod image targets (backend `prod`, backend `scheduler`, frontend `prod`)
- [ ] CD hardening: `git fetch --tags`, export `APP_VERSION`, `pg_dump` before `alembic upgrade head`
- [ ] Documented rollback (`git checkout <tag>` + rebuild) in [setup/deployment.md](../setup/deployment.md)
- [ ] `release.yml`: tag push → `gh release create --generate-notes`
- [ ] Drop the "lands with Phase 6 Slice D" qualifier in [AGENTS.md](../../AGENTS.md) once `release.yml` exists, and make it a link

### Toolchain hygiene

Surfaced while wiring CI up; none of it blocks the deploy, all of it is cheap to fold in here.

- [x] GitHub Actions bumped off the deprecated Node 20 runtime (2026-07-27) — checkout v7, setup-node v7, pnpm/action-setup v6, setup-uv v9.0.0. **setup-uv must be pinned to a full version**: it stopped publishing floating major tags after v7 as a supply-chain measure, so `@v9` does not resolve.
- [x] pnpm aligned at 11 across CI and `frontend/Dockerfile` (2026-07-27) — CI was on 10.
- [x] uv pinned to the same version in CI and `backend/Dockerfile` (2026-07-27) — CI installed the latest uv while the image pinned 0.11.22, so `uv.lock` was resolved by a different uv than the one building the images. Bump both together.
- [ ] **Decide on `pnpm install --no-frozen-lockfile` in CI.** It defeats lockfile integrity checking, so a green CI does not prove the lockfile is honest; `frontend/Dockerfile` already uses `--frozen-lockfile`. Left alone because flipping it breaks CI if the lockfile is genuinely out of sync — verify locally first.
- [ ] *(optional)* `packageManager` field in `frontend/package.json` to single-source the pnpm version instead of repeating it in `ci.yml` and the Dockerfile. Note `pnpm/action-setup` errors when both `packageManager` and the `version` input are set, so the input must go at the same time.

## Slice E — First deploy

**Acceptance:** the app loads over HTTPS on a phone, the PWA installs, `/api/health` reports ok with a version, and the scheduler container runs both ETL jobs. Full detail in [setup/deployment.md](../setup/deployment.md) §3–5.

- [ ] Repo cloned to `/opt/tfm` (the path `cd.yml` assumes)
- [ ] Server-side `.env` files written with **every secret rotated** — fresh `SECRET_KEY`, new `POSTGRES_PASSWORD`, `ENVIRONMENT=production`, `APP_DEBUG=false`, `SESSION_COOKIE_SECURE=true`, empty `CORS_ALLOW_ORIGINS`, prod `APP_BASE_URL` / `GOOGLE_REDIRECT_URI`; copies kept in a password manager
- [ ] Database bootstrapped from the latest seed dump — **never re-seed**, the REVE catalogue takes ~12 days under the 5 req/hr cap
- [ ] `up -d --build` + `alembic upgrade head`
- [ ] Verified: site on a phone, PWA installs, `/api/health` returns the version, `logs scheduler` shows supercronic loading both jobs

## Slice F — External services on the prod origin

**Acceptance:** Google sign-in and verification email both work against the production domain, for users other than the account owner.

- [ ] Google OAuth client: `https://<domain>` as authorised origin, `https://<domain>/api/auth/google/callback` as redirect URI
- [ ] **Consent screen published to Production** — scopes are non-sensitive (`userinfo.profile`, `userinfo.email`), so no Google verification and no warning screen; while in Testing only listed test users can sign in
- [ ] Resend: sending domain verified, `MAIL_FROM` set — without it verification mail only reaches the owner's inbox
- [ ] `up -d --force-recreate backend` (Compose snapshots env at container creation; a restart keeps stale values)

## Slice G — Close the CI/CD loop

**Acceptance:** merging a PR to `main` deploys to production automatically, and `main` cannot be pushed to directly or force-pushed.

- [ ] Repo secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS` (`ssh-keyscan <host>`)
- [ ] CD workflow re-enabled in the Actions tab (disabled since 2026-07-08, no server to target)
- [ ] Branch protection ruleset on `main`: **require a pull request**, require the CI checks, block force-push and deletion
- [ ] **End-to-end test:** trivial PR → merge → CI green → CD deploys → the version string in production changes. The only proof the pipeline works.

## Slice H — Security gate, cutover, first release

**Acceptance:** the infra-0001 pre-deploy gate passes, the laptop is no longer part of production, and `v0.1.0` is tagged.

- [ ] `/security-review` run; infra-0001 gate passed (HSTS, only 22/80/443 open, no published `5432`, secrets rotated, cookie `Secure`, CORS empty, backup restorable)
- [ ] Laptop crontab refresh/PVPC lines removed — the scheduler container owns them now
- [ ] `backup_db_cron.sh` moved to the server crontab (needs `rclone` + B2 config on the VPS; its hardcoded paths adjusted)
- [ ] **`v0.1.0` tagged**
- [ ] infra-0001 flipped to `accepted`; B2 lifecycle rule added on `tfm-db-backups`

## Open question

Whether to keep registration invite-only during the demo window. Email verification already blocks drive-by signups, so this is a judgement call rather than a gap — decide before the URL is shared.

## Deferred out of this phase

**Map viewport loading** (open-on-position + zoom-gated `bbox` fetch + padded cache, with a small backend `bbox` on `GET /api/points/map`) was listed under Phase 6 in PLAN.md. It is a frontend feature with no deployment dependency and is tracked in [features.md](../features.md); it should not block the deploy.
