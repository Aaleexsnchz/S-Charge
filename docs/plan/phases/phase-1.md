# Phase 1 — Foundation

Per [plan.md](../plan.md): Docker Compose, FastAPI + Postgres + Alembic, auth (email/password + Google OAuth) with email verification + password reset via Resend, audit logging, plus a React + Vite + MUI frontend scaffold with auth pages and PWA installability.

Slices 1–3 ship the auth backend; Slice 4 is the frontend scaffold.

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Email/password auth | Done | #1 |
| 2 | Google OAuth | Done | direct to `main` |
| 3 | Email verification + password reset | Done | direct to `main` |
| 4 | Frontend scaffold | Done | #2 |

Decisions: [auth-0001](../../decisions/auth-0001-fastapi-users.md) · [auth-0002](../../decisions/auth-0002-cookie-session.md) · [auth-0003](../../decisions/auth-0003-preregistration-shell-mitigation.md) · [fe-0002](../../decisions/fe-0002-pwa.md).

## Slice 1 — Email/password auth [x]

**Acceptance:** register → verify email link → login → `/api/users/me` → logout. Audit emits `register` and `login_ok`. Invalid credentials return a single generic 401 regardless of whether the email exists.

- [x] Docker Compose, FastAPI app factory, Postgres + Alembic baseline
- [x] User model + Alembic migration with the `citext` extension
- [x] fastapi-users wiring: UserManager, single CookieTransport + JWTStrategy backend, PasswordHelper at OWASP-min Argon2id
- [x] Auth routes mounted under `/api/auth`; `/api/users/me` reachable
- [x] Audit helper emitting JSON to stdout on a dedicated audit logger

## Slice 2 — Google OAuth [x]

**Acceptance:** "Sign in with Google" lands the user authenticated with the same HttpOnly session cookie. First-time Google users are auto-provisioned in `oauth_account`; existing email accounts link Google without duplication.

- [x] `oauth_account` table via fastapi-users mixin; `User.oauth_accounts` eager-loaded
- [x] `httpx-oauth` Google client + `get_oauth_router(associate_by_email=True)` mounted at `/api/auth/google`
- [x] `CookieRedirectTransport` returning 303 → `/profile` so the top-level callback navigation isn't blank

## Slice 3 — Email verification + password reset [x]

**Acceptance:** unverified password registrations can't log in until they click the verify link. `/forgot-password` triggers a Resend email; `/reset-password?token=…` completes the flow. The pre-registration shell attack is mitigated.

- [x] Email helper sending via Resend; failures emit `email_send_failed` instead of 500-ing
- [x] `on_after_register` triggers `request_verify`; verify + reset routers mounted; auth router gains `requires_verification=True`
- [x] Google OAuth router gains `is_verified_by_default=True`
- [x] `UserManager.oauth_callback` override wipes `hashed_password` when linking an unverified password row

## Slice 4 — Frontend scaffold [x]

**Acceptance:** `pnpm dev` serves a Vite-built React + MUI app at `:5173`. The auth pages (login, register, check-email, verify-email, forgot-password, reset-password) call the backend and surface its error codes in Spanish. Auth state available via a router-level loader. PWA installable on iOS Safari and Chrome.

- [x] Vite + React + TypeScript scaffold with ESLint + Prettier; dev proxy forwarding `/api/*` to the backend container
- [x] MUI v9 (Emotion) theme set up; self-hosted fonts; per-icon imports preserved
- [x] Typed API client (openapi-typescript + openapi-fetch); `pnpm gen:api` regenerates from the backend's `/openapi.json`
- [x] React Router v8 with an auth-aware root loader (`GET /api/users/me`); public / protected layout split
- [x] Six auth pages wired to backend error codes (`LOGIN_BAD_CREDENTIALS`, `LOGIN_USER_NOT_VERIFIED`, `REGISTER_USER_ALREADY_EXISTS`, `RESET_PASSWORD_BAD_TOKEN`, etc.); Spanish copy throughout
- [x] PWA manifest + service worker; install prompt on Chrome, "Add to Home Screen" launches standalone on iOS Safari
