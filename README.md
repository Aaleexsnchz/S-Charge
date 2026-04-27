# TFM — EV Charging PWA

A master's thesis project (IoT): a Progressive Web App for managing EV charging points, combining real data from the **REVE API** (the Spanish public charging network) with historical sessions from **ACN-Data** (the Adaptive Charging Network research dataset), plus user-contributed private charging points with simulated occupation.

The academic contribution lives in phases 3–4 (data integration, session simulation, and charging-schedule optimisation). Authentication, infrastructure, and business-feature scaffolding are kept deliberately library-backed — see [docs/auth-decisions.md](docs/auth-decisions.md) and [docs/future-work.md](docs/future-work.md) for the explicit scope record.

## Status

| Phase | Status |
|---|---|
| 0 — Tooling setup | ✅ done |
| 1 — Foundation (auth, schema, core UI) | 🚧 slices 1–4 done; slice 5 pending |
| 2 — REVE + Map | ⏳ not started |
| 3 — ACN import + analytics | ⏳ not started |
| 4 — Simulation + algorithm | ⏳ not started |
| 5 — Private points + bookings | ⏳ not started |
| 6 — Polish + deployment | ⏳ not started |
| 7 — Thesis writing | ⏳ not started |

See [PLAN.md](PLAN.md) for the full phase breakdown and estimates.

## Quick start

```bash
# clone and prepare env
git clone <repo> tfm && cd tfm
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# start all services
docker compose up
```

Services:

- **Backend API** — <http://localhost:8000> (OpenAPI docs at `/docs`)
- **Frontend** — <http://localhost:5173>
- **Postgres** — exposed on `:5432` for host-side tools

See [DOCKER.md](DOCKER.md) for when to rebuild vs. recreate the containers after a change.

To enable **Google sign-in** on `/login`, follow the [Google OAuth setup](#google-oauth-setup) section below. To deliver verification and password-reset emails, follow the [Email provider setup](#email-provider-setup) section.

### Google OAuth setup

The backend supports Google sign-in side by side with email/password; both flows land on the same HttpOnly session cookie. To enable it locally, create an OAuth 2.0 Client in Google Cloud Console and paste the credentials into `backend/.env`.

1. Open [APIs & Services → OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent). Set **User type: External** (Internal restricts sign-in to a Google Workspace org and rejects personal Gmail with `403 org_internal`). Fill in App name, support email, and developer contact. While the app is in **Testing**, add every Google account you'll use as a **Test user**, otherwise consent is denied.
2. Enable the **People API** for the same project: <https://console.cloud.google.com/apis/library/people.googleapis.com>. The Python `httpx-oauth` Google client fetches the user profile from `people.googleapis.com`, not the legacy `/oauth2/v3/userinfo` endpoint, so without this the OAuth callback fails with `GetProfileError → GetIdEmailError` after Google has already issued the access token.
3. Go to **APIs & Services → Credentials** and click **Create credentials → OAuth client ID**. Application type: **Web application**.
4. Fill in:
   - **Authorised JavaScript origins:** `http://localhost:5173`
   - **Authorised redirect URIs:** `http://localhost:5173/api/auth/google/callback`
5. Copy the generated **Client ID** and **Client Secret** into `backend/.env`:

   ```env
   GOOGLE_CLIENT_ID=<paste>
   GOOGLE_CLIENT_SECRET=<paste>
   GOOGLE_REDIRECT_URI=http://localhost:5173/api/auth/google/callback
   ```

6. Recreate the backend so it reads the new env vars: `docker compose up -d --force-recreate backend`. (`docker compose restart` is **not** sufficient — Compose snapshots env vars at container creation, so a restart keeps the old empty values and Google rejects the authorize request with `Missing required parameter: client_id`.)

"Iniciar sesión con Google" on `/login` will now bounce through Google and return you to the app authenticated. The redirect URI points at the Vite dev server (`:5173`), not the backend directly (`:8000`); Vite proxies `/api/*` to the backend so the session cookie lands on the same origin as the SPA. Phase 6 will swap these localhost URLs for the production domain.

**Browser note for testing.** Run the OAuth flow from a regular browser tab. Google's "secure browsers" policy returns `403 disallowed_useragent` when the user-agent looks like an embedded webview — including Edge/Chrome DevTools' device-emulation toolbar (e.g. iPhone 12 Pro), in-IDE preview panels, and mobile in-app browsers. Toggle device emulation off for the consent step, then re-enable it for layout testing once you're authenticated.

### Email provider setup

The backend sends verification and password-reset emails through [Resend](https://resend.com). Without an API key, registration still succeeds but the helper logs `email_send_failed` instead of delivering — fine for UI sanity-checking, not enough to exercise the verify or reset success paths. Decision rationale: [docs/auth-decisions §13](docs/auth-decisions.md#13-email-verification-and-password-reset-slice-3-2026-04-27).

1. Create an account at <https://resend.com> and copy a key from **API Keys**. Free tier is 100 emails/day, sufficient for the thesis demo.
2. Add the credentials to `backend/.env`:

   ```env
   RESEND_API_KEY=<paste>
   MAIL_FROM=onboarding@resend.dev
   APP_BASE_URL=http://localhost:5173
   ```

3. Recreate the backend so it reads the new env vars: `docker compose up -d --force-recreate backend`. (`docker compose restart` is **not** sufficient — see the OAuth section above for the same gotcha.)

**Sandbox sender.** `onboarding@resend.dev` works without DNS setup but, in test mode, Resend only delivers to the email address that owns the Resend account. Register through the UI with that same email to receive the verification link.

**Production setup (phase 6).** Once the production domain exists, verify it in Resend's **Domains** dashboard, add the SPF/DKIM/DMARC records they provide to your DNS, and switch `MAIL_FROM` to a sender on that domain. Inbox placement (especially Gmail) depends on those records — without DKIM, transactional mail tends to land in spam.

## Tech stack

**Backend.** FastAPI, SQLAlchemy 2.0 (async via asyncpg), Alembic, Pydantic v2, fastapi-users for authentication, pwdlib + argon2-cffi for password hashing. Package manager: `uv`. Lint/typecheck: `ruff` + `mypy`.

**Frontend.** React + Vite + TypeScript, MUI, React Router v7 (data-router APIs: loaders, actions, lazy routes), `openapi-typescript` + `openapi-fetch` for the typed API client, `notistack` for toasts. Auth state lives in a root loader — no client-side store. TanStack Query lands in phase 2 for non-auth server state. PWA installability via `vite-plugin-pwa` (phase 1 slice 4). Decisions: [docs/frontend-decisions.md](docs/frontend-decisions.md). Package manager: `pnpm`.

**Database.** PostgreSQL 16 with the `citext` extension (case-insensitive email lookup).

**Deployment.** Single Hetzner VPS (CX22), Nginx + Let's Encrypt. Deliberately rejected: Kubernetes, Vercel, Supabase — all overkill for thesis scope.

## Monorepo layout

```text
tfm/
├── backend/         FastAPI + Postgres backend — see backend/CLAUDE.md
├── frontend/        React + Vite + MUI frontend — see frontend/CLAUDE.md
├── docs/            Decision records, slice plans, future-work catalogue
├── docker-compose.yml
├── PLAN.md          Project scope, phases, deliverables, estimates
├── CONTRIBUTING.md  Branch naming, commit conventions, workflow
└── DOCKER.md        When to rebuild / recreate / do nothing
```

## Key architectural decisions

- **Authentication: single JWT in an HttpOnly cookie** via `fastapi-users` — no dual-token dance, no refresh tokens. Full 12-section decision record in [docs/auth-decisions.md](docs/auth-decisions.md); deferred security hardening in [docs/future-work.md](docs/future-work.md).
- **Rate limiting: deferred to Nginx `limit_req`** at the reverse proxy, not in application code. See [auth-decisions §7](docs/auth-decisions.md).
- **Payments and real-time occupation: simulated.** The thesis contribution is simulation and algorithm work, not payment integration. See the *Mocked* section in [PLAN.md](PLAN.md).
- **Deployment: single VPS.** Nginx terminates TLS, reverse-proxies to `uvicorn`, serves the built PWA statically. See [PLAN.md](PLAN.md) phase 6.

## Documentation index

- **[PLAN.md](PLAN.md)** — phases, deliverables, estimates
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — branch naming, Conventional Commits format, workflow
- **[DOCKER.md](DOCKER.md)** — when to rebuild, recreate, or do nothing after a change
- **[docs/auth-decisions.md](docs/auth-decisions.md)** — security decision record (ADR-style, 12 sections)
- **[docs/phase-1.md](docs/phase-1.md)** — slice-by-slice auth task plan
- **[docs/future-work.md](docs/future-work.md)** — items deliberately out of thesis scope
- **[docs/screens.md](docs/screens.md)** — UI screen specifications
- **[backend/CLAUDE.md](backend/CLAUDE.md)** / **[frontend/CLAUDE.md](frontend/CLAUDE.md)** — package-specific conventions and file layouts

## License

Master's thesis project; licensing to be determined before any public release.
