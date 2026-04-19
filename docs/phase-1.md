# Phase 1 — Foundation

Task breakdown for [PLAN.md](../PLAN.md) Phase 1. Organized as vertical slices: each slice is an independently demoable deliverable with a single acceptance criterion and cross-domain sub-tasks underneath.

## Definition of Done (applies to every slice)

- Migration runs clean from a fresh DB (`alembic upgrade head`)
- Backend: `ruff check` + `mypy` pass; new routes covered by at least one test
- Frontend: `tsc -b` + `eslint` pass; manually exercised in the browser
- `docker compose up` from a clean clone still works end-to-end
- Committed with Conventional Commits (`feat(backend): …`, `feat(frontend): …`, etc.), one logical change per commit

---

## Slice 1 — Email/password auth via fastapi-users with HttpOnly session cookie

Decisions and rationale are recorded in [auth-decisions.md](auth-decisions.md). This slice implements them via `fastapi-users` natively — no custom endpoints in Slice 1, since the library handles login, logout, and register directly when composed with a single cookie-backed `AuthenticationBackend`.

**Acceptance:** a new visitor can register, receives an HttpOnly session cookie (`HttpOnly; Secure; SameSite=Lax`; 14-day TTL), calls protected `GET /api/users/me`, and logs out via `POST /api/auth/logout` (cookie cleared). Invalid credentials return `400 LOGIN_BAD_CREDENTIALS` — same status and detail whether the email exists or not (no email-exists oracle). Duplicate email returns `400 REGISTER_USER_ALREADY_EXISTS`. Missing or malformed session cookie on a protected endpoint returns `401`. All error codes follow fastapi-users' convention: a single `400` discriminated by a machine-readable `detail` enum. All backend endpoints are under the `/api/*` prefix for consistency with `/api/health`.

**Locked decisions** (full rationale in [auth-decisions.md](auth-decisions.md))
- UUID v4 PK (library default, `uuid.uuid4`); `citext` email; Argon2id via `pwdlib`; HS256 JWT
- Single JWT session in HttpOnly cookie (`HttpOnly; Secure; SameSite=Lax`; 14-day TTL); no refresh tokens (see auth-decisions §6)
- Length-only password policy (≥ 12 chars)
- Stdlib JSON audit logging on auth events
- Rate limiting deferred to Nginx `limit_req` (phase 6 infra); per-account lockout, DB-backed session revocation, and persisted audit table are explicit future work

### Task plan

Ordered commits, each small and self-contained. Files listed are relative to the repo root. Each task ends with a concrete deliverable that can be checked off.

After task 1 is merged, tasks 2–4 / 7 / 8 / 9 have no mutual ordering constraint; the sequence below is the recommended walk. Strict dependency chain: 1 → 2 → 5 → 6 → 10 → 11 → 12 → 13/14.

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

**8. `feat(backend): add jwt strategy and auth backend`**

- Files: `backend/app/utils/auth_backend.py`
- Deliverable: single module containing the JWT strategy factory (`get_jwt_strategy()` — 14-day lifetime, HS256 algorithm, `tfm:session` audience), `CookieTransport` (HttpOnly, Secure, SameSite=Lax, path `/`, `cookie_max_age` matching JWT lifetime), and the composed `AuthenticationBackend`. Module-level constants (`ALGORITHM`, `TOKEN_AUDIENCE`, `COOKIE_NAME`) pin the security-relevant non-env values. Also renames the session settings from `refresh_*` to `session_*` in `app/config.py` + `backend/.env.example` + `backend/.env`, and drops now-unused settings (`access_token_expire_minutes`, `refresh_token_expire_days`, `refresh_cookie_path`).

**9. `feat(backend): add audit logger`**

- Files: `backend/app/utils/audit.py`
- Deliverable: `audit(event, **fields)` helper emitting JSON log lines to stdout via stdlib `logging` + `python-json-logger`. No rate limiter — rate limiting is deferred to Nginx in phase 6 (auth-decisions §7).

**10. `feat(backend): add auth schemas and user manager`**

- Files: `backend/app/schemas/auth.py`, `backend/app/services/user_manager.py`, `backend/app/dependencies.py` (extend)
- Deliverable: `UserRead` / `UserCreate` / `UserUpdate` subclassing fastapi-users' bases, with `name` / `picture_url` fields and an email validator that trims and lowercases. `UserManager(BaseUserManager[User, UUID])` overrides `validate_password` (length ≥ 12) and emits audit events in `on_after_register` / `on_after_login`. `get_user_db` dependency added alongside `get_db` (wraps the session in `SQLAlchemyUserDatabase(session, User)`).

**11. `feat(backend): mount fastapi-users auth routers`**

- Files: `backend/app/routers/auth.py`, `backend/app/routers/users.py`, `backend/app/services/user_manager.py` (extend)
- Deliverable: split router files by URL prefix — `routers/auth.py` mounts `get_auth_router` (login/logout) and `get_register_router` under `/auth`; `routers/users.py` mounts `get_users_router` under `/users`. The shared `FastAPIUsers[User, UUID]` instance (composed from auth backend + user manager) is added to `services/user_manager.py` alongside the existing `UserManager`, together with `current_user = fastapi_users.current_user(active=True)` for task 12 to re-export. No rate-limiting decorators — nothing custom to wrap.

**12. `feat(backend): wire auth routers into main`**

- Files: `backend/app/main.py`
- Deliverable: both routers (`app.routers.auth`, `app.routers.users`) mounted via `app.include_router(..., prefix="/api")` so the full surface lives under `/api/*` (matching `/api/health`). `/docs` shows all auth endpoints (`POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/users/me`, etc.); `/api/health` still returns 200. No re-export of `current_user` through `dependencies.py` — consumers import directly from `app.services.user_manager`.

**13. `test(backend): happy path auth flow`**

- Files: `backend/tests/test_auth_happy.py`
- Deliverable: end-to-end test — register → login (captures session cookie) → `GET /api/users/me` (200) → `POST /api/auth/logout` → `GET /api/users/me` (401, cookie cleared).

**14. `test(backend): auth negative paths`**

- Files: `backend/tests/test_auth_negative.py`
- Deliverable: tests cover duplicate email (`400 REGISTER_USER_ALREADY_EXISTS`); wrong password and non-existent email (both `400 LOGIN_BAD_CREDENTIALS` — same response proves no email-exists oracle); password shorter than 12 chars (`400 REGISTER_INVALID_PASSWORD` with our length-policy message); missing or malformed session cookie on `/api/users/me` (`401`). Expired-cookie case is deferred because deterministic testing requires time-mocking or per-test settings overrides; not worth the complexity for marginal coverage. All paths under `/api/*`.

#### Frontend

**15. `feat(frontend): add api client with auth store`**

- Files: `frontend/src/api/client.ts`, `frontend/src/auth/AuthStore.ts`
- Deliverable: fetch wrapper with `credentials: 'include'` so the HttpOnly session cookie is sent automatically; on 401 clears the auth store and redirects to `/login`. No client-side token handling — the cookie is the session. Zustand store holds only the `user` object (fetched from `GET /users/me`) and exposes `login`, `register`, `logout`, `bootstrap`. `grep -r localStorage frontend/src/api frontend/src/auth` returns no matches.

**16. `feat(frontend): add protected route and bootstrap`**

- Files: `frontend/src/components/ProtectedRoute.tsx`, `frontend/src/main.tsx`
- Deliverable: `ProtectedRoute` renders children when `user` is set, shows a loading state while `bootstrap` is pending, redirects to `/login` otherwise. App root invokes `AuthStore.bootstrap()` once on mount.

**17. `feat(frontend): add login and register pages`**

- Files: `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/RegisterPage.tsx`
- Deliverable: MUI forms for each; inline error mapping for 400/401/409 to human-readable messages (429 is handled generically if/when Nginx rate-limiting is enabled in phase 6); successful submit routes to `/profile`.

**18. `feat(frontend): wire auth routes`**

- Files: `frontend/src/router.tsx`
- Deliverable: `/login`, `/register`, `/profile` routes; `/profile` wrapped in `ProtectedRoute` and renders the `user` from the store.

#### Docs

**19. `docs(backend): document auth architecture`**

- Files: `backend/CLAUDE.md`, `backend/.env.example` (final pass)
- Deliverable: short "Auth architecture" section in `backend/CLAUDE.md` cross-referencing [auth-decisions.md](auth-decisions.md) and this slice; `backend/.env.example` confirmed to include every setting introduced in tasks 3 and 8 (session JWT + cookie flags).

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
