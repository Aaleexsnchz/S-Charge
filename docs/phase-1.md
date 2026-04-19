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

### Task plan

Ordered commits, each small and self-contained. Files listed are relative to the repo root. Each task ends with a concrete deliverable that can be checked off.

After task 1 is merged, tasks 2–4 / 7 / 8 / 9 have no mutual ordering constraint; the sequence below is the recommended walk. Strict dependency chain: 1 → 2 → 5 → 6 → 10 → 11 → 12 → 13 → 14/15.

#### Backend

**1. `chore(backend): add auth dependencies`**

- Files: `backend/pyproject.toml`, `backend/uv.lock`
- Deliverable: `fastapi-users[sqlalchemy]`, `argon2-cffi`, `slowapi`, `python-json-logger` declared and locked. `uv sync --locked` passes inside the backend container.

**2. `chore(backend): wire alembic to app metadata`**

- Files: `backend/alembic/env.py`
- Deliverable: `app.models` imported and `target_metadata = Base.metadata`. A dry-run `uv run alembic revision --autogenerate -m probe` produces a non-empty (but discarded) diff.

**3. `feat(backend): add auth settings`**

- Files: `backend/app/config.py`, `backend/.env.example`
- Deliverable: new settings — `jwt_algorithm`, `access_token_expire_minutes`, `refresh_token_expire_days`, `refresh_cookie_name`, `refresh_cookie_secure`, `refresh_cookie_path`. `backend/.env.example` updated. Existing `secret_key` reused for JWT signing.

**4. `test(backend): add transactional db fixture`**

- Files: `backend/tests/conftest.py`
- Deliverable: async engine + per-test transaction rollback + `httpx.AsyncClient` app-level fixture. A trivial smoke test using the client returns 200 from `/api/health`.

**5. `feat(backend): add user model with citext email`**

- Files: `backend/app/models/user.py`, `backend/app/models/__init__.py`
- Deliverable: `User(SQLAlchemyBaseUserTableUUID)` with `email: Mapped[str] = mapped_column(CITEXT, unique=True, index=True)`, plus `name`, `last_login_at`, `picture_url`. `is_verified` (inherited from the mixin) is the verification flag — no separate `email_verified_at` timestamp. Imported in `__init__.py` so Alembic sees it.

**6. `feat(backend): initial auth migration`**

- Files: `backend/alembic/versions/xxxx_auth_initial.py`
- Deliverable: migration executes `CREATE EXTENSION IF NOT EXISTS citext` then creates `users`. `alembic upgrade head` runs clean on a fresh DB and `alembic downgrade base` reverts cleanly.

**7. `feat(backend): add argon2id password helper`**

- Files: `backend/app/utils/security.py`
- Deliverable: `password_helper = PasswordHelper(...)` exposed at module level, wrapping pwdlib's `Argon2Hasher(memory_cost=19456, time_cost=2, parallelism=1)` to match OWASP minimums (tuned down from argon2-cffi defaults for CX22 login latency). No custom protocol class — fastapi-users' `PasswordHelper` already implements `PasswordHelperProtocol` and pwdlib handles auto-rehash on verify.

**8. `feat(backend): add jwt strategies and auth transports`**

- Files: `backend/app/utils/jwt_strategy.py`, `backend/app/utils/auth_backends.py`
- Deliverable: two `JWTStrategy` instances (access: `aud="users:access"`, 15 min; refresh: `aud="users:refresh"`, 14 d); `BearerTransport` for access; `CookieTransport` scoped to `/auth/refresh` with `HttpOnly`, `Secure`, `SameSite=Lax`; `AuthenticationBackend` composed for access flow.

**9. `feat(backend): add audit logger and rate limiter`**

- Files: `backend/app/utils/audit.py`, `backend/app/services/rate_limit.py`
- Deliverable: `audit(event, **fields)` helper emitting JSON log lines via stdlib `logging` + `python-json-logger`; `limiter = Limiter(key_func=get_remote_address)` instance.

**10. `feat(backend): add auth schemas and user manager`**

- Files: `backend/app/schemas/auth.py`, `backend/app/services/user_manager.py`
- Deliverable: `UserRead` / `UserCreate` / `UserUpdate` subclassing fastapi-users' bases, with `name` / `picture_url` fields and an email validator that trims and lowercases. `UserManager(BaseUserManager[User, UUID])` overrides `validate_password` (length ≥ 12) and emits audit events in `on_after_register` / `on_after_login`.

**11. `feat(backend): mount fastapi-users auth routers`**

- Files: `backend/app/routers/auth.py`
- Deliverable: `FastAPIUsers` instance composed from auth backend + user manager + schemas; include `get_register_router`, `get_auth_router`, `get_users_router` under `/auth` and `/users`. Register decorated with `limiter.limit("10/hour")`; login with `limiter.limit("5/minute")`.

**12. `feat(backend): add refresh endpoint with cookie rotation`**

- Files: `backend/app/routers/auth.py` (extend)
- Deliverable: `POST /auth/refresh` reads the refresh cookie, validates via refresh `JWTStrategy`, issues a new access token and rotates the cookie; rate-limited `30/minute`. `POST /auth/logout` clears the refresh cookie and emits a `logout` audit event.

**13. `feat(backend): wire auth router and rate limit middleware`**

- Files: `backend/app/main.py`, `backend/app/dependencies.py`
- Deliverable: auth router registered under `/auth`; `SlowAPIMiddleware` + 429 exception handler installed; `get_current_user = fastapi_users.current_user(active=True)` re-exported from `dependencies.py`. `/docs` shows all auth endpoints; `/api/health` still returns 200.

**14. `test(backend): happy path auth flow`**

- Files: `backend/tests/test_auth_happy.py`
- Deliverable: end-to-end test — register → login (captures bearer token + refresh cookie) → `GET /auth/me` (200) → `POST /auth/refresh` (new token + new cookie) → `POST /auth/logout` → `GET /auth/me` with old token (401).

**15. `test(backend): auth negative paths`**

- Files: `backend/tests/test_auth_negative.py`
- Deliverable: tests cover duplicate email; wrong password (with timing-equivalence guard — existing- and missing-user latencies within 2× of each other); missing / malformed / expired access token; refresh token presented at a protected endpoint (wrong audience); password shorter than 12 chars; 6th login attempt within 60s returns 429.

#### Frontend

**16. `feat(frontend): add api client with auth store`**

- Files: `frontend/src/api/client.ts`, `frontend/src/auth/AuthStore.ts`
- Deliverable: fetch wrapper with `credentials: 'include'`, injects in-memory access token as `Authorization: Bearer`; on 401 attempts `POST /auth/refresh` once and retries; on second 401 clears state. Zustand store holds `user` + `accessToken` **in memory only** and exposes `login`, `register`, `logout`, `bootstrap`. `grep -r localStorage frontend/src/api frontend/src/auth` returns no matches.

**17. `feat(frontend): add protected route and bootstrap`**

- Files: `frontend/src/components/ProtectedRoute.tsx`, `frontend/src/main.tsx`
- Deliverable: `ProtectedRoute` renders children when `user` is set, shows a loading state while `bootstrap` is pending, redirects to `/login` otherwise. App root invokes `AuthStore.bootstrap()` once on mount.

**18. `feat(frontend): add login and register pages`**

- Files: `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/RegisterPage.tsx`
- Deliverable: MUI forms for each; inline error mapping for 400/401/409/429 to human-readable messages; successful submit routes to `/profile`.

**19. `feat(frontend): wire auth routes`**

- Files: `frontend/src/router.tsx`
- Deliverable: `/login`, `/register`, `/profile` routes; `/profile` wrapped in `ProtectedRoute` and renders the `user` from the store.

#### Docs

**20. `docs(backend): document auth architecture`**

- Files: `backend/CLAUDE.md`, `backend/.env.example` (final pass)
- Deliverable: short "Auth architecture" section in `backend/CLAUDE.md` cross-referencing [auth-decisions.md](auth-decisions.md) and this slice; `backend/.env.example` confirmed to include every new variable introduced in task 3.

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
