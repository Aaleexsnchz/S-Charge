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
| **Resend** | Transactional email (verification, password reset). Sandbox sender works with no DNS; one helper module wraps it, so swapping providers is a small change. |
| **`httpx`** | Async HTTP for the REVE and REE clients. |
| **Uvicorn** | ASGI server, in dev with reload and in the prod image. |
| **pytest + pytest-asyncio + pytest-httpx** | Tests; external APIs are stubbed at the transport, never called for real in CI. |
| **uv** | Package manager and lockfile. One fast tool for resolve, install and run — pinned to the same version in CI and in the image so the lockfile is always resolved by the uv that builds it. |
| **Ruff** | Lint + format in one Rust binary, replacing flake8/isort/black. |
| **basedpyright** | Type checking. Runs in CI and in the pre-push hook, not on commit — it is too slow to sit between typing a message and getting a prompt back. |
| **supercronic** | Cron inside the scheduler container: logs to stdout, no host crontab to provision. Chosen over APScheduler ([infra-0001](decisions/infra-0001-deployment.md)). |

## Frontend

> **The frontend stack is mid-migration.** [Phase 6](plan.md) replaces MUI + Emotion with Tailwind + shadcn/ui, React Router with TanStack Router, and adds a form layer the app never had. The **Status** column says what is in the tree today: *shipped* is running, *Phase 6* is not installed yet, *leaving* is what it replaces. Full rationale, alternatives and the measurement plan: [thesis/migracion-del-stack.md](thesis/migracion-del-stack.md).

| Tool | Status | Why |
| --- | --- | --- |
| **React + TypeScript** | shipped | The default for a component-heavy PWA, and the ecosystem everything below assumes. |
| **Vite** | shipped | Dev server with instant HMR, and the production build. Proxies `/api/*` in dev so the session cookie stays first-party. |
| **TanStack Query** ([fe-0004](decisions/fe-0004-tanstack-query.md)) | shipped | Server state: cache, deduplication, stale-while-revalidate, retries and consistent pending/error states, defined once instead of re-implemented per page with `useEffect`. The map's large point payload is fetched once and shared across visits within a session. |
| **openapi-typescript + openapi-fetch** | shipped | Types generated from the backend's own OpenAPI schema (`pnpm run gen:api`), so a backend contract change breaks the frontend build instead of production. |
| **MapLibre GL JS + OpenFreeMap** | shipped | The map: WebGL rendering and native clustering for ~13.7k points, no API key, no usage cap. Unaffected by the migration. ADR: [fe-0003](decisions/fe-0003-maplibre-openfreemap.md). |
| **`vite-plugin-pwa` (Workbox)** | shipped | Manifest + service worker for installability. The PWA-instead-of-native decision has an ADR: [fe-0002](decisions/fe-0002-pwa.md). |
| **`@fontsource` (Hanken Grotesk, JetBrains Mono)** | shipped | Self-hosted fonts — no third-party request on load, and figures render mono so numbers line up. |
| **Vitest** | shipped | Tests, sharing Vite's transform pipeline. |
| **Biome** ([fe-0006](decisions/fe-0006-biome.md)) | shipped | Lint, format and import sorting in one pinned Rust binary, replacing ESLint + Prettier — the same consolidation Ruff and uv give the backend, so the mental model matches across both halves of the repo. Its `recommended` set is stricter than what it replaced (a11y rules, `noArrayIndexKey`). |
| **pnpm** | shipped | Package manager; content-addressed store, strict by default. Pinned via `packageManager` so CI and the image agree. |
| **Tailwind CSS v4** | Phase 6 | Styling. Build-time CSS instead of Emotion's runtime CSS-in-JS: no styling engine in the bundle, nothing to serialise per render. The s-charge design tokens are re-expressed as Tailwind theme tokens — same design, different implementation. |
| **shadcn/ui** (+ Base UI primitives) | Phase 6 | Components are **copied into the repo**, not imported, so adapting the design system means editing our own files rather than overriding a vendor's from outside. Accessibility comes from the underlying headless primitives. |
| **lucide-react** | Phase 6 | Icons, tree-shakeable per import — the same rule the MUI icon ban enforced, without the barrel hazard. |
| **TanStack Router** | Phase 6 | Compile-time typed route params and validated search params, turning a class of runtime bug into a build error; shares conventions with TanStack Query. Keeps the auth bootstrap in a root loader. |
| **TanStack Form + Zod** | Phase 6 | The app has no form layer; the point-registration wizard is the first real form. One Zod schema validates client-side and mirrors what Pydantic enforces server-side. |
| **sonner** | Phase 6 | Toasts, replacing notistack. |
| **MUI v9 + Emotion** ([fe-0001](decisions/fe-0001-mui.md), superseded by [fe-0007](decisions/fe-0007-frontend-stack-migration.md)), MUI X Charts, notistack, React Router v8 | leaving | What Phase 6 removes. MUI carried the app from zero to a working product on a fixed timeline and is being replaced for cost-per-new-screen and runtime-styling reasons, not because it failed — see the chapter. |

## Infrastructure

| Tool | Why |
| --- | --- |
| **PostgreSQL 18** | Relational data with real constraints, plus `citext` for case-insensitive email lookup. Bumped from 17 for three things this project actually uses: `uuidv7()` (time-ordered keys, better index locality than the random v4 ids in use), temporal `WITHOUT OVERLAPS` primary keys (booking overlaps become a database constraint instead of application logic with a race), and the new asynchronous I/O subsystem. Rationale: [thesis/migracion-del-stack.md](thesis/migracion-del-stack.md). CI and production run 18; the dev volume is still 17 until it is cut over in Phase 5, because **a major upgrade needs a dump/restore, not a tag flip** — see [operations.md](operations.md). |
| **Docker Compose** | Runs Postgres in dev and the whole stack in production, so the deployed artifact is built from this repo and can be smoke-tested locally (`just prod-up`). Details: [operations.md](operations.md). |
| **Caddy** | Reverse proxy in production: automatic Let's Encrypt certificates, HTTP→HTTPS redirect, HSTS, and same-origin serving of the SPA and `/api/*`. See [infra-0001](decisions/infra-0001-deployment.md). |
| **nginx** (frontend prod image only) | Serves the built `dist/` with SPA fallback. Caddy does the routing; nginx just serves files. |
| **GitHub Actions** | CI (lint, typecheck, tests, prod image builds) and CD (deploy on a successful CI run on `main`). |
| **lefthook** | Git hooks: staged-file lint/format with auto-restage on commit, and a pre-push hook mirroring CI exactly, which `just ci` also runs. Installs as a uv dev dependency. Replaced pre-commit, whose cross-language env management this repo never used. |
| **betterleaks** | Secret scanning. Best-effort locally, authoritative as a CI job over full history. |
| **Renovate** *(Phase 5)* | Weekly grouped dependency PRs, gated by the same CI as everything else. No automerge — merging to `main` deploys. |
| **just** | Task runner for humans — `just api`/`just web` to run the app, `just ci` before pushing. Nothing in CI/CD depends on it. |
| **rclone + Backblaze B2** | Offsite database backups from the host. |
