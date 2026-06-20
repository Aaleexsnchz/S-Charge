# TFM — EV Charging PWA

A master's thesis project (IoT): a Progressive Web App for managing EV charging points. Combines real data from the **REVE API** (the Spanish public charging network) with historical sessions from **ACN-Data** (the Adaptive Charging Network research dataset), plus user-contributed private charging points with simulated occupation.

## Status

| Phase | Status |
| --- | --- |
| 1 — Foundation | `[x]` done |
| 2 — REVE seed + Map | `[~]` shipped + QA'd on real devices; seed cron mid-run (tariffs); post-seed incremental refresh ready |
| 3 — ACN import (internal) | `[~]` ingest backend shipped; real import + analysis notebook need `ACN_API_TOKEN` |
| 4 — Simulation + Algorithm | `[~]` slices 1–2 shipped (vehicle catalogue + PVPC ingest); 3–5 pending |
| 5 — Private points, Bookings + Sessions | `[ ]` not started |
| 6 — Polish + Deployment | `[ ]` not started |
| 7 — Thesis writing | `[ ]` not started |

See [docs/PLAN.md](docs/PLAN.md) for phase descriptions, acceptance criteria, and estimates.

## Quick start

```bash
git clone <repo> tfm && cd tfm
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

docker compose up
```

Services:

- **Backend API** — <http://localhost:8000> (OpenAPI docs at `/docs`)
- **Frontend** — <http://localhost:5173> (Vite proxies `/api/*` to the backend so the session cookie stays first-party)
- **Postgres** — exposed on `:5432` for host-side tools

See [docs/DOCKER.md](docs/DOCKER.md) for when to rebuild vs. recreate the containers after a change.

To enable **Google sign-in**, follow [Google OAuth setup](#google-oauth-setup). To deliver verification and password-reset emails, follow [Email provider setup](#email-provider-setup).

## Tech stack

**Backend** — Python 3.12+, FastAPI, SQLAlchemy 2.0 (async via asyncpg), Alembic, Pydantic v2, fastapi-users for authentication. Package manager: `uv`. Lint/typecheck: `ruff` + `mypy`.

**Frontend** — React + Vite + TypeScript + MUI v7 (Emotion), in `frontend/`. Package manager: `pnpm`.

**Database** — PostgreSQL 17 with the `citext` extension (case-insensitive email lookup).

## Repo layout

```text
tfm/
├── backend/             FastAPI + Postgres backend
├── frontend/            React + Vite + MUI v7 PWA
├── docs/
│   ├── PLAN.md          Project scope, phases, acceptance criteria
│   ├── DOCKER.md        When to rebuild / recreate / do nothing
│   ├── SKILLS.md        Claude Code skills installed in this repo
│   ├── decisions/       Architectural decision records
│   ├── thesis/          Concept-level chapters for the thesis writeup
│   └── phases/          Per-phase task plans
├── docker-compose.yml
├── README.md
└── CLAUDE.md            Project memory for Claude Code (also covers git workflow)
```

## Key architectural decisions

See [docs/decisions/](docs/decisions/) for the explicit scope record.

## Google OAuth setup

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

## Email provider setup

The backend sends verification and password-reset emails through [Resend](https://resend.com). Without an API key, registration still succeeds but the helper logs `email_send_failed` instead of delivering — fine for UI sanity-checking, not enough to exercise the verify or reset success paths. Decision rationale: [docs/decisions/auth-0003](docs/decisions/auth-0003-preregistration-shell-mitigation.md).

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

## Documentation index

- [docs/PLAN.md](docs/PLAN.md) — phases, acceptance criteria, estimates
- [docs/decisions/](docs/decisions/) — architectural decision records
- [docs/thesis/](docs/thesis/) — concept-level chapters for the thesis writeup
- [docs/phases/](docs/phases/) — per-phase task plans
- [docs/DOCKER.md](docs/DOCKER.md) — when to rebuild, recreate, or do nothing
- [docs/SKILLS.md](docs/SKILLS.md) — Claude Code skills installed in this repo
- [CLAUDE.md](CLAUDE.md) — project memory for Claude Code (covers git workflow)

## License

Master's thesis project; licensing to be determined before any public release.
