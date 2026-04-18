# Phase 1 — Foundation

Task breakdown for [PLAN.md](../PLAN.md) Phase 1. Organized as vertical slices: each slice is an independently demoable deliverable with a single acceptance criterion and cross-domain sub-tasks underneath.

## Definition of Done (applies to every slice)

- Migration runs clean from a fresh DB (`alembic upgrade head`)
- Backend: `ruff check` + `mypy` pass; new routes covered by at least one test
- Frontend: `tsc -b` + `eslint` pass; manually exercised in the browser
- `docker compose up` from a clean clone still works end-to-end
- Committed with Conventional Commits (`feat(backend): …`, `feat(frontend): …`, etc.), one logical change per commit

---

## Slice 1 — Email/password auth via fastapi-users with httpOnly refresh cookie

Decisions and rationale are recorded in [auth-decisions.md](auth-decisions.md). This slice implements them via `fastapi-users` with targeted custom code where the library defaults don't match.

**Acceptance:** a new visitor can register, receives an access token (JSON body) and a refresh cookie (`HttpOnly; Secure; SameSite=Lax` scoped to `/auth/refresh`), calls protected `GET /auth/me`, refreshes their session via `POST /auth/refresh`, and logs out (cookie cleared). Invalid credentials return a generic 401 (no email-exists oracle). Duplicate email returns 409. Per-IP rate-limit triggers return 429.

**Locked decisions** (full rationale in [auth-decisions.md](auth-decisions.md))
- UUID v4 PK; `citext` email; Argon2id (`argon2-cffi`); HS256 JWT with audience claim
- Access token in response body, in-memory on client; refresh in HttpOnly cookie scoped to `/auth/refresh`
- 15 min access TTL, 14 day refresh TTL, stateless rotation
- Per-IP rate limits (login 5/min, register 10/hr, refresh 30/min) via `slowapi`
- Length-only password policy (≥ 12 chars)
- Stdlib JSON audit logging on auth events
- Per-account lockout, DB-tracked refresh rotation, and persisted audit table are explicit future work

**Backend — deps**
- [ ] Add: `fastapi-users[sqlalchemy]`, `argon2-cffi`, `slowapi`, `python-json-logger`

**Backend — config**
- [ ] Extend [app/config.py](../backend/app/config.py) with `jwt_algorithm`, `access_token_expire_minutes`, `refresh_token_expire_days`, `refresh_cookie_name`, `refresh_cookie_secure` (overridable for local dev), `refresh_cookie_path = "/auth/refresh"`
- [ ] Reuse existing `secret_key` for JWT signing

**Backend — models & migration**
- [ ] [app/models/user.py](../backend/app/models/user.py): subclass fastapi-users' `SQLAlchemyBaseUserTableUUID` and override the `email` column to use `CITEXT`; add `name`, `last_login_at`, `email_verified_at` (nullable, populated by Slice 2 OAuth flow), `picture_url` (nullable, Slice 2)
- [ ] Register the model in [app/models/__init__.py](../backend/app/models/__init__.py) so autogenerate sees it
- [ ] Wire [alembic/env.py](../backend/alembic/env.py) to import `app.models` and set `target_metadata = Base.metadata`
- [ ] Alembic revision: `CREATE EXTENSION IF NOT EXISTS citext`, create `users`

**Backend — security wiring**
- [ ] [app/utils/security.py](../backend/app/utils/security.py): `Argon2PasswordHelper` thin wrapper conforming to fastapi-users' `PasswordHelperProtocol`, using OWASP-recommended Argon2id parameters (`memory_cost=19456`, `time_cost=2`, `parallelism=1`); auto-rehash on verify
- [ ] [app/utils/jwt_strategy.py](../backend/app/utils/jwt_strategy.py): two `JWTStrategy` instances — access (15 min, audience `users:access`) and refresh (14 d, audience `users:refresh`)
- [ ] [app/utils/auth_backends.py](../backend/app/utils/auth_backends.py): `BearerTransport` for access; `CookieTransport` for refresh (HttpOnly, Secure, SameSite=Lax, scoped path)
- [ ] [app/utils/audit.py](../backend/app/utils/audit.py): `audit(event, **fields)` helper backed by stdlib `logging` + `python-json-logger`; events `register`, `login_ok`, `login_fail`, `refresh_ok`, `logout`
- [ ] [app/services/user_manager.py](../backend/app/services/user_manager.py): `UserManager` subclass overriding `validate_password` (length ≥ 12), and `on_after_register` / `on_after_login` to emit audit events
- [ ] [app/services/rate_limit.py](../backend/app/services/rate_limit.py): `slowapi` `Limiter` instance + decorators

**Backend — schemas**
- [ ] [app/schemas/auth.py](../backend/app/schemas/auth.py): subclass fastapi-users' `BaseUser` / `BaseUserCreate` / `BaseUserUpdate` with our extra fields (`name`, `picture_url`); add Pydantic validator on `email` to trim and lowercase

**Backend — routes**
- [ ] [app/routers/auth.py](../backend/app/routers/auth.py): mount fastapi-users' built-in routers (`get_register_router`, `get_auth_router`, `get_users_router`) under `/auth` and `/users`
- [ ] Add custom `POST /auth/refresh` (reads cookie, validates refresh JWT, mints new access token, rotates refresh cookie) and `POST /auth/logout` (clears cookie + audit) — both rate-limited
- [ ] Register router in [app/main.py](../backend/app/main.py); register `slowapi` middleware and exception handler

**Backend — dependencies**
- [ ] [app/dependencies.py](../backend/app/dependencies.py): re-export fastapi-users' `current_active_user` as `get_current_user` so the rest of the codebase has a stable name

**Backend — tests**
- [ ] Pytest fixture for transactional test DB (new test infra — used by every future slice)
- [ ] Happy path: register → login → `/auth/me` → refresh → logout
- [ ] Duplicate email → 409
- [ ] Wrong password → 401; existing-user and missing-user response latencies are within 2× of each other (timing-equivalence guard)
- [ ] Missing / malformed / bad-signature / expired access token → 401
- [ ] Refresh happy path returns new access token and rotates cookie
- [ ] Refresh with missing / expired / wrong-audience cookie → 401
- [ ] Logout clears cookie
- [ ] Rate limit: 6th login within 1 min from the same IP → 429
- [ ] Password shorter than 12 chars → 400 with clear message

**Frontend**
- [ ] [api/client.ts](../frontend/src/api/client.ts): fetch wrapper with `credentials: 'include'`, injects in-memory access token as `Authorization: Bearer`; on 401 attempts `POST /auth/refresh` once and retries; on second 401 clears state and redirects to `/login`
- [ ] [auth/AuthStore.ts](../frontend/src/auth/AuthStore.ts) (Zustand or context): holds `user` and `accessToken` **in memory only**; exposes `login`, `register`, `logout`, `bootstrap` (calls `/auth/refresh` on app mount and, if successful, loads `/auth/me`)
- [ ] [components/ProtectedRoute.tsx](../frontend/src/components/ProtectedRoute.tsx): waits for `bootstrap` to finish, then renders children or redirects
- [ ] [pages/LoginPage.tsx](../frontend/src/pages/LoginPage.tsx) + [pages/RegisterPage.tsx](../frontend/src/pages/RegisterPage.tsx): MUI forms mapping 400/401/409/429 to inline human-readable errors
- [ ] Add `/login`, `/register`, `/profile` routes; `/profile` is protected and shows `user`
- [ ] Enforced in code review: the access token must never be written to `localStorage` or `sessionStorage`

**Infra / docs**
- [ ] Add to [backend/.env.example](../backend/.env.example): `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `REFRESH_COOKIE_NAME`, `REFRESH_COOKIE_SECURE`
- [ ] Once the code lands, add a short "Auth architecture" section to [backend/CLAUDE.md](../backend/CLAUDE.md) cross-referencing [auth-decisions.md](auth-decisions.md) so later slices inherit the rules

---

## Slice 2 — Google OAuth via fastapi-users + httpx-oauth

Cross-ref: decision §12 in [auth-decisions.md](auth-decisions.md) (`oauth_account` join table).

**Acceptance:** clicking "Sign in with Google" on the login page returns the user to the app authenticated, receiving the same access token + refresh cookie pair that email/password login issues. First-time Google users are auto-provisioned with a row in `users` (no password) and a row in `oauth_account`. Returning users match by `(oauth_name, account_id)`. An existing email/password user whose Google email matches can link Google without creating a duplicate account. OAuth `state` mismatches return 400.

**Backend — deps**
- [ ] Add: `httpx-oauth`

**Backend — models & migration**
- [ ] Extend [app/models/user.py](../backend/app/models/user.py) to mix in fastapi-users' `SQLAlchemyBaseOAuthAccountTableUUID` relationship
- [ ] Add [app/models/oauth_account.py](../backend/app/models/oauth_account.py) using fastapi-users' base table
- [ ] Alembic migration adding `oauth_account` table

**Backend — routes**
- [ ] Configure `httpx_oauth.clients.google.GoogleOAuth2` with `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
- [ ] Mount fastapi-users' `get_oauth_router(google_client, auth_backend, SECRET, redirect_url=...)` at `/auth/google` — provides `/auth/google/authorize` and `/auth/google/callback`
- [ ] Wire the callback to set the refresh cookie via the existing cookie transport (same backend as Slice 1) and redirect to `/auth/callback` on the frontend
- [ ] Audit-log a `oauth_login_ok` event in `on_after_login`
- [ ] Tests: callback with mocked Google userinfo — new user, existing oauth_account, email-link, mismatched `state` → 400

**Frontend**
- [ ] "Sign in with Google" button on `LoginPage` and `RegisterPage` → navigates to `/auth/google/authorize`
- [ ] `/auth/callback` page calls `AuthStore.bootstrap()` (the cookie was set server-side during the OAuth callback) and redirects to `/profile`

**Infra / docs**
- [ ] Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` to [backend/.env.example](../backend/.env.example)
- [ ] Document in root [README.md](../README.md): Google Cloud Console steps (OAuth consent screen, authorized origins `http://localhost:5173`, redirect `http://localhost:8000/auth/google/callback`)

---

## Slice 3 — PWA installable

**Acceptance:** in Chrome desktop/Android, the "Install app" prompt appears on the running app. On iOS Safari, "Add to Home Screen" produces an icon that launches the app full-screen with the correct theme color.

**Frontend**
- [ ] Add deps: `vite-plugin-pwa`, `workbox-window`
- [ ] Configure `vite-plugin-pwa` in [vite.config.ts](../frontend/vite.config.ts): manifest `name`, `short_name`, `description`, `theme_color`, `background_color`, `display: standalone`, `start_url: /`
- [ ] Generate PWA icons into `frontend/public/`: `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `apple-touch-icon.png`
- [ ] Update [index.html](../frontend/index.html): `<meta name="theme-color">`, `<link rel="apple-touch-icon">`
- [ ] Register service worker in `main.tsx` (auto-update strategy)

**Verification**
- [ ] Chrome DevTools → Application → Manifest: no warnings
- [ ] Chrome Android: install prompt appears
- [ ] iOS Safari: "Add to Home Screen" launches standalone

---

## Slice 4 — README onboarding in ≤5 commands

**Acceptance:** a fresh clone of the repo produces a working stack following ≤5 shell commands from the root [README.md](../README.md). The Google OAuth setup has its own linked section.

**Docs**
- [ ] Write root `README.md`: one-paragraph project summary, link to [PLAN.md](../PLAN.md)
- [ ] "Quickstart" section: the ≤5 commands (e.g. `cp backend/.env.example backend/.env`, `cp frontend/.env.example frontend/.env`, edit secrets, `docker compose up`, open `http://localhost:5173`)
- [ ] "Google OAuth setup" subsection: Cloud Console steps + where each value goes in the env files
- [ ] Link to [CONTRIBUTING.md](../CONTRIBUTING.md), [DOCKER.md](../DOCKER.md)
- [ ] Sanity-check by cloning into a temp dir and running through the steps

---

## Suggested order

1. Slice 1 first — it's the backbone; Slice 2 builds on its schema and context
2. Slice 2 — adds columns to `users`, reuses `AuthContext`
3. Slice 3 in parallel with Slice 2 if blocked (independent of backend)
4. Slice 4 last — by then the real commands are stable
