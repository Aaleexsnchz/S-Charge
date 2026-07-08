---
id: infra-0001
status: proposed
phase: Phase 6
date: 2026-06
related: [auth-0002, fe-0002]
---

# infra-0001: Deploy the Docker Compose stack on a single small VPS behind Caddy

> Append revisions below with date and reason rather than editing in place.

## Revisions

**2026-06-30 — Scheduling moves from host cron into an in-container scheduler service.** Supersedes the "host cron / systemd timer" choice in **Decision** and **Implementation** (the `Cron:` bullet). The refresh ETL will run from a dedicated `scheduler` service in `docker-compose.prod.yml` — the same backend image, running [supercronic](https://github.com/aptible/supercronic) (or a small APScheduler entrypoint) and invoking `python -m scripts.refresh_reve` / the PVPC ingest **directly inside the container** (no `docker compose exec` hop) — logging to **stdout**.

*Why.* With host cron, the job runs via `docker compose exec`, whose output attaches to the host caller, not the container: ETL logs never appear in `docker compose logs` and instead accumulate in a host file (`~/.reve-seed.log`) that **no one rotates** (it grows unbounded) and that lives separately from the app's own logs. Moving the scheduler into a service means: (1) ETL logs ride the container log stream (`docker compose logs -f scheduler`), one place, with the platform's logging driver handling rotation/retention; (2) **no host crontab to provision** on the VPS — the stack is self-contained and portable (survives a host move or a future migration to Fly/k8s). Cost is one extra small container plus a cron-syntax file checked into the repo. Surfaced while investigating a REVE-side 504 regression where the host-file log was the only window into the cron's behaviour.

*Unchanged:* single VPS + Caddy + GitHub Actions CD, and the host-level ops scripts (DB backup) per [DOCKER.md](../DOCKER.md) stay on the host. Only the **REVE/PVPC refresh scheduling** moves into the container.

**2026-07-08 — Implementation choices, as built.** Three refinements to the letter (not the substance) of **Implementation**:

- *Scheduler = supercronic* (not APScheduler): a `scheduler` Docker stage extends the backend `prod` image with the pinned supercronic binary and a repo-committed [crontab](../../backend/crontab); no Python scheduler code to write or keep alive. The unused `apscheduler` dependency was removed.
- *`docker-compose.prod.yml` is a standalone file, not an override.* Compose file merging appends to `ports:` rather than replacing, so an override cannot cleanly *unpublish* Postgres's `5432` (the security gate's hard requirement) without recent-compose `!reset` tags. A standalone file with its own project name is unambiguous and lets the prod stack be smoke-tested next to the dev stack locally.
- CD is gated on CI: `deploy.yml` became [cd.yml](../../.github/workflows/cd.yml) triggered by `workflow_run` on a **successful** CI run on `main` (push-triggered deploy would race the tests).

Provisioning runbook: [setup/deployment.md](../setup/deployment.md).

**Status note.** Proposed — the architecture (single always-on VPS + Caddy + GitHub Actions CD + host cron) is decided; the specific host (Hetzner vs. Oracle Always-Free) is confirmed at provisioning. The thesis *scaling* strategy (how this would grow to many users) is a separate written artifact; this ADR governs the live demo deployment only.

**Decision.** Run the existing `docker compose` stack (Postgres + FastAPI backend + built frontend) on **one small always-on Linux VPS**. A reverse proxy ([Caddy](https://caddyserver.com/)) terminates TLS with automatic Let's Encrypt certificates and serves the frontend and `/api/*` from a **single origin**. The REVE/PVPC refresh ETL runs from the server's own cron (or a systemd timer), independent of any laptop. CI/CD is GitHub Actions: the existing test matrix gates every push; merging to `main` triggers an SSH deploy (`git pull` → `docker compose up -d --build` → `alembic upgrade head`). Default host: **Hetzner CX22** (~€4/mo, EU); fallback **Oracle Cloud Always-Free** (ARM Ampere, €0) if a zero-cost requirement dominates.

**Rationale.** Constraints: 1–2 users (just me at first, a couple at the live demo), minimal or zero spend, must be secure, must keep the refresh cron running with my laptop closed, and must give a real HTTPS URL openable on a phone. A single VPS is the tightest fit:

- *Same artifact I already run.* The app is `docker compose` (three services + a cron). A VPS runs that unchanged — no re-platforming, no serverless rewrite, no splitting the stack.
- *Makes the cron laptop-independent.* The biggest practical reason to deploy: `refresh_reve.py` and the PVPC ingest move to a host that is on 24/7, so the catalogue stays fresh without my machine awake. (Today they run from the laptop's cron — see [thesis/planificacion-de-siembra.md](../thesis/planificacion-de-siembra.md).)
- *Same-origin keeps the session model simple and safe.* Auth is a single HttpOnly cookie ([auth-0002](auth-0002-cookie-session.md)). Serving the SPA and the API from one domain behind one proxy avoids `SameSite=None` cross-site cookies and broad CORS — fewer moving parts and a smaller attack surface than a split frontend/backend.
- *HTTPS is required anyway.* The PWA ([fe-0002](fe-0002-pwa.md)) and browser geolocation both need a secure context; Caddy provides and auto-renews certificates with near-zero config.
- *Cost is ~€4/mo or €0*, with no per-service multiplication and no free-tier sleeping.

**Implementation (Phase 6).**

- Host: Hetzner CX22 (2 vCPU / 4 GB, EU — good data locality for a Spanish thesis) or Oracle Always-Free ARM. Domain via a cheap registrar (~€10/yr) or a free DuckDNS subdomain; optional Cloudflare (free) for DNS.
- Reverse proxy: Caddy in the compose — `:443` serves the frontend static build and proxies `/api/*` to the backend; automatic TLS + HTTP→HTTPS redirect.
- A `docker-compose.prod.yml` override: build the frontend `prod` (static/nginx) and backend targets, **drop the `5432` host port** so Postgres is reachable only on the internal network, inject secrets from a server-side `.env` (never committed).
- CI/CD: keep the current CI (`.github/workflows/ci.yml`); add a `deploy.yml` that, on push to `main`, SSHes in and runs pull + `up -d` + `alembic upgrade head`. GitHub Secrets hold the SSH key and deploy config.
- Cron: move the refresh lines to the server crontab / a systemd timer (host-level `scripts/`, per [DOCKER.md](../DOCKER.md)).
- Releases: tag `vMAJOR.MINOR.PATCH`; `main` is always deployable; **`v1.0.0` is the evaluated build**.

**Pre-deploy security gate** (must pass before first public exposure; run `/security-review`):

- HTTPS + HSTS; HTTP→HTTPS redirect.
- Host firewall: only 80/443 + SSH; SSH key-only, root login disabled, fail2ban.
- Postgres not published to the host; strong DB password; backups confirmed (Backblaze B2 already configured).
- Secrets server-side only; dev secrets rotated; Google OAuth redirect URI + Resend sender set for the prod origin.
- Cookie `Secure` + `SameSite=Lax`; CORS locked to the one origin; auth rate limits kept.
- Optionally keep registration invite-only during the demo (email verification already blocks drive-by signups).

**Rejected alternatives.**

- *Vercel (frontend) + a separate backend.* Vercel is excellent for static/SPA hosting (global CDN, free TLS, preview deploys) and could host the Vite build for free. But it is serverless / front-end-oriented: it does not run a long-lived FastAPI process, Postgres, or a rate-limited multi-hour ETL well (function time limits, cold starts; Vercel Cron is coarse and time-boxed). Using it forces a split origin (`SameSite=None` + CORS) and still leaves the backend, database and cron to host elsewhere — more parts, more attack surface, no demo-visible gain at this scale. It *is* a sensible scale-up path for the frontend (noted in the scaling chapter).
- *Supabase (managed Postgres / BaaS).* Tempting to offload Postgres. But the free tier **pauses the project after ~a week of inactivity** (fatal for an always-on demo + cron) and caps at 500 MB; Pro is $25/mo (beyond "minimal"). I already have a working, thesis-documented auth stack ([auth-0001](auth-0001-fastapi-users.md)/[auth-0002](auth-0002-cookie-session.md)) and an Alembic-managed schema, so Supabase Auth / edge functions would mean rewriting a *pillar* of the thesis for no benefit. At most I'd use its bare Postgres — which I already run for free in Compose with backups. Net: adds cost/dependency, removes the all-in-one-box simplicity.
- *Container PaaS — Render / Railway / Fly.io.* The closest managed option. Render's free web service **sleeps** on idle and its free Postgres **expires after 90 days**; Railway is usage-based past a small credit; Fly.io fits Docker + volumes + scheduled machines but its free allowances shrank and its managed-Postgres story is in flux. For three services + cron, a single VPS is cheaper and simpler, and sleeping instances break both the PWA demo and the cron. Fly is the strongest runner-up if managed infra is wanted later.
- *Big-cloud (AWS/GCP/Azure) or managed Kubernetes / ECS.* 12-month trials then real bills, plus orchestration overhead that is pure overkill for 1–2 users. Belongs in the scaling chapter as the theoretical growth path, not the live deploy.
- *Split static-CDN frontend + VPS API (Cloudflare Pages / Netlify + VPS).* Genuinely free, fast frontend, but reintroduces cross-origin cookie/CORS complexity for no benefit at demo scale. Revisit only when CDN edge-caching actually matters.

**References.**

- [PLAN.md](../PLAN.md) — Phase 6 (Polish + Deployment) and the scaling-strategy artifact.
- [auth-0002](auth-0002-cookie-session.md) cookie session; [fe-0002](fe-0002-pwa.md) PWA (secure-context requirement).
- [thesis/planificacion-de-siembra.md](../thesis/planificacion-de-siembra.md) — why the refresh runs on a schedule (and why a server, not a laptop, should host it).
- Caddy automatic HTTPS; Hetzner Cloud; Oracle Cloud Always Free.
