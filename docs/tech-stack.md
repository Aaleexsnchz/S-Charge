# Tech stack

Every library and tool the project depends on, and the reason it is there. Every entry here has a one-line reason. Where the choice also has an ADR, the row links to it — which of the two a decision belongs in is settled in [decisions/README.md](decisions/README.md).

Versions live in `backend/pyproject.toml` and `frontend/package.json`. This document does not repeat them.

## Backend

| Tool | Why |
| --- | --- |
| **Python 3.13** | Bumped from 3.12 in Phase 5. Chosen over 3.14 because it is what the agent/LLM SDK ecosystem targets, and the AI phase depends on it. |
| **FastAPI** | Async, Pydantic-native, generates the OpenAPI schema the frontend's types are built from. |
| **SQLAlchemy 2.0 (async, asyncpg)** | Mature ORM with a typed 2.0 API; async all the way to the driver so the ETL and the API share one engine. |
| **Alembic** | Migrations that come with SQLAlchemy; autogenerate then review, never trust the diff. |
| **Pydantic v2 + pydantic-settings** | Request/response schemas and typed env configuration from one library. |
| **`fastapi-users`** | Authentication. Load-bearing enough to have an ADR: [auth-0001](decisions/auth-0001-fastapi-users.md). |
| **`httpx-oauth`** | Google OAuth client, the provider `fastapi-users` expects. |
| **Argon2 (`argon2-cffi`)** | Password hashing at OWASP-minimum parameters — see [auth-0001](decisions/auth-0001-fastapi-users.md). |
| **`limits`** | Rate limiting on the auth endpoints, used directly as a FastAPI dependency. Replaces `slowapi`, whose way of reaching `fastapi-users`' generated routes fails silently ([auth-0004](decisions/auth-0004-rate-limits-and-client-ip.md)). |
| **Resend** | Transactional email (verification, password reset). Sandbox sender works with no DNS; one helper module wraps it, so swapping providers is a small change. |
| **`httpx`** | Async HTTP for the REVE and REE clients. |
| **Uvicorn** | ASGI server, in dev with reload and in the prod image. |
| **pytest + pytest-asyncio + pytest-httpx** | Tests; external APIs are stubbed at the transport, never called for real in CI. |
| **uv** | Package manager and lockfile. One fast tool for resolve, install and run — pinned to the same version in CI and in the image so the lockfile is always resolved by the uv that builds it. |
| **Ruff** | Lint + format in one Rust binary, replacing flake8/isort/black. |
| **basedpyright** | Type checking. Runs in CI and in the pre-push hook, not on commit — it is too slow to sit between typing a message and getting a prompt back. |
| **supercronic** | Cron inside the scheduler container: logs to stdout, no host crontab to provision. Chosen over APScheduler ([infra-0001](decisions/infra-0001-deployment.md)). |

## Frontend

| Tool | Status | Why |
| --- | --- | --- |
| **React + TypeScript** | shipped | The default for a component-heavy PWA, and the ecosystem everything below assumes. |
| **Vite** | shipped | Dev server with instant HMR, and the production build. Proxies `/api/*` in dev so the session cookie stays first-party. |
| **TanStack Query** ([fe-0004](decisions/fe-0004-tanstack-query.md)) | shipped | Server state: cache, deduplication, stale-while-revalidate, retries and consistent pending/error states, defined once instead of re-implemented per page with `useEffect`. The map's large point payload is fetched once and shared across visits within a session. |
| **openapi-typescript + openapi-fetch** | shipped | Types generated from the backend's own OpenAPI schema, which is exported to a committed `openapi.json` (`just gen-api`) so the contract is reviewable in a diff and CI can fail on drift, rather than the frontend discovering it at runtime. |
| **MapLibre GL JS + OpenFreeMap** | shipped | The map: WebGL rendering and native clustering for ~13.7k points, no API key, no usage cap. Unaffected by the migration. ADR: [fe-0003](decisions/fe-0003-maplibre-openfreemap.md). |
| **`vite-plugin-pwa` (Workbox)** | shipped | Manifest + service worker for installability. The PWA-instead-of-native decision has an ADR: [fe-0002](decisions/fe-0002-pwa.md). |
| **`@fontsource` (Hanken Grotesk, JetBrains Mono)** | shipped | Self-hosted fonts — no third-party request on load, and figures render mono so numbers line up. |
| **Vitest** | shipped | Tests, sharing Vite's transform pipeline. |
| **Biome** ([fe-0006](decisions/fe-0006-biome.md)) | shipped | Lint, format and import sorting in one pinned Rust binary, replacing ESLint + Prettier — the same consolidation Ruff and uv give the backend, so the mental model matches across both halves of the repo. Its `recommended` set is stricter than what it replaced (a11y rules, `noArrayIndexKey`). |
| **pnpm** | shipped | Package manager; content-addressed store, strict by default. Pinned via `packageManager` so CI and the image agree. |
| **MUI v9 + Emotion** ([fe-0001](decisions/fe-0001-mui.md)) | shipped | Component library. Buys accessible form controls, dialogs, bottom sheets and navigation — with focus rings and ARIA — without writing them, which is where a solo project on a fixed timeline should not spend its hours. Emotion is its styling engine. |
| **React Router** | shipped | Routing and per-route data loading; the auth bootstrap is a root loader. |
| **MUI X Charts** | shipped | Charts. Nothing renders a chart on real data yet, so this is a placeholder choice. |
| **notistack** | shipped | Toasts. |

## Infrastructure

| Tool | Why |
| --- | --- |
| **PostgreSQL 18** | Relational data with real constraints, plus `citext` for case-insensitive email lookup. Bumped from 17 for the asynchronous I/O subsystem, in use today, and for temporal `WITHOUT OVERLAPS` primary keys, which would make booking conflicts a schema invariant if the parked booking idea is ever built ([decisions/README.md](decisions/README.md) → Records worth writing later). **`uuidv7()` was evaluated and rejected**: its gain is insert locality, and the largest table here is ~47k rows seeded once against roughly two dozen inserts a day, so the difference is unmeasurable — ids stay application-side v4, and adopting it would mean either rewriting every existing id across nine tables and their foreign keys or carrying two UUID versions in one column. The one place it would still be worth taking is the sessions and bookings tables: they are the first with a real insert rate, so they can be born with the server-side default if it earns itself there. Dev, CI and production all run 18; **a major upgrade is a dump/restore and a mount-path change, not a tag flip** — see [operations.md](operations.md). |
| **Docker Compose** | Runs Postgres in dev and the whole stack in production, so the deployed artifact is built from this repo and can be smoke-tested locally (`just prod-up`). Details: [operations.md](operations.md). |
| **Caddy** | Reverse proxy in production: automatic Let's Encrypt certificates, HTTP→HTTPS redirect, HSTS, and same-origin serving of the SPA and `/api/*`. See [infra-0001](decisions/infra-0001-deployment.md). |
| **nginx** (frontend prod image only) | Serves the built `dist/` with SPA fallback. Caddy does the routing; nginx just serves files. |
| **GitHub Actions** | CI (lint, typecheck, tests, prod image builds), CD (deploy on a tag push, or on demand — [infra-0003](decisions/infra-0003-deploy-on-tag.md)) and a release workflow turning a tag into GitHub Release notes. |
| **lefthook** | Git hooks: staged-file lint/format with auto-restage on commit, and a pre-push hook mirroring CI exactly, which `just ci` also runs. Installs as a uv dev dependency. Replaced pre-commit, whose cross-language env management this repo never used. |
| **betterleaks** | Secret scanning. Best-effort locally, authoritative as a CI job over full history. |
| **Renovate** | Weekly grouped dependency PRs, gated by the same CI as everything else. Base images are pinned by digest, and the versions this repository pins twice — uv, Python, Node — move in one PR through custom managers. No automerge — a dependency bump should be a deliberate merge, and it reaches production with the next tag ([infra-0003](decisions/infra-0003-deploy-on-tag.md)). Chosen over Dependabot, which cannot read `uv.lock` at all: [infra-0004](decisions/infra-0004-renovate-over-dependabot.md). |
| **just** | Task runner for humans — `just api`/`just web` to run the app, `just ci` before pushing. Nothing in CI/CD depends on it. |
| **rclone + Backblaze B2** | Offsite database backups from the host. |
