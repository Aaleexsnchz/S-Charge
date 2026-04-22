# Phase 1 — Foundation

Task breakdown for [PLAN.md](../PLAN.md) Phase 1. Organized as vertical slices: each slice is an independently demoable deliverable with a single acceptance criterion and cross-domain sub-tasks underneath. Check off tasks as you commit them so progress is visible at a glance.

## Definition of Done (applies to every slice)

- Migration runs clean from a fresh DB (`alembic upgrade head`)
- Backend: `ruff check` + `ruff format --check` + `mypy` pass; new routes covered by at least one test
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

Ordered commits, each small and self-contained. After task 1 is merged, tasks 2–4 / 7 / 8 / 9 have no mutual ordering constraint; the sequence below is the recommended walk. Strict dependency chain — backend: 1 → 2 → 5 → 6 → 10 → 11 → 12 → 13/14; frontend: 15 → {16, 17} → 18.

#### Backend

- [x] **1. `chore(backend): add auth dependencies`**
  - Files: `backend/pyproject.toml`, `backend/uv.lock`
  - Deliverable: `fastapi-users[sqlalchemy]`, `argon2-cffi`, `slowapi`, `python-json-logger` declared and locked. `uv sync --locked` passes inside the backend container. *(slowapi later became unused when rate limiting moved to Nginx — can be removed in a follow-up cleanup.)*

- [x] **2. `chore(backend): wire alembic to app metadata`**
  - Files: `backend/alembic/env.py`
  - Deliverable: `app.models` imported and `target_metadata = Base.metadata`. A dry-run `uv run alembic revision --autogenerate -m probe` produces a non-empty (but discarded) diff.

- [x] **3. `feat(backend): add auth settings`**
  - Files: `backend/app/config.py`, `backend/.env.example`
  - Deliverable: new settings — `jwt_algorithm`, `access_token_expire_minutes`, `refresh_token_expire_days`, `refresh_cookie_name`, `refresh_cookie_secure`, `refresh_cookie_path`. `backend/.env.example` updated. Existing `secret_key` reused for JWT signing. *(Settings later simplified in task 8 once the architecture moved to single-cookie.)*

- [x] **4. `test(backend): add transactional db fixture`**
  - Files: `backend/tests/conftest.py`
  - Deliverable: async engine + per-test transaction rollback + `httpx.AsyncClient` app-level fixture. A trivial smoke test using the client returns 200 from `/api/health`.

- [x] **5. `feat(backend): add user model with citext email`**
  - Files: `backend/app/models/user.py`, `backend/app/models/__init__.py`
  - Deliverable: `User(SQLAlchemyBaseUserTableUUID)` with `email: Mapped[str] = mapped_column(CITEXT, unique=True, index=True)`, plus `name`, `last_login_at`, `picture_url`. `is_verified` (inherited from the mixin) is the verification flag — no separate `email_verified_at` timestamp. Imported in `__init__.py` so Alembic sees it.

- [x] **6. `feat(backend): initial auth migration`**
  - Files: `backend/alembic/versions/xxxx_auth_initial.py`
  - Deliverable: migration executes `CREATE EXTENSION IF NOT EXISTS citext` then creates `users`. `alembic upgrade head` runs clean on a fresh DB and `alembic downgrade base` reverts cleanly.

- [x] **7. `feat(backend): add argon2id password helper`**
  - Files: `backend/app/utils/security.py`
  - Deliverable: `password_helper = PasswordHelper(...)` exposed at module level, wrapping pwdlib's `Argon2Hasher(memory_cost=19456, time_cost=2, parallelism=1)` to match OWASP minimums. No custom protocol class — fastapi-users' `PasswordHelper` already implements `PasswordHelperProtocol` and pwdlib handles auto-rehash on verify.

- [x] **8. `feat(backend): add jwt strategy and auth backend`**
  - Files: `backend/app/utils/auth_backend.py`, `backend/app/config.py`, `backend/.env.example`, `backend/.env`
  - Deliverable: single module containing the JWT strategy factory (`get_jwt_strategy()` — 14-day lifetime, HS256 algorithm, `tfm:session` audience), `CookieTransport` (HttpOnly, Secure, SameSite=Lax, path `/`, `cookie_max_age` matching JWT lifetime), and the composed `AuthenticationBackend`. Module-level constants (`ALGORITHM`, `TOKEN_AUDIENCE`, `COOKIE_NAME`) pin the security-relevant non-env values. Also renames the session settings from `refresh_*` to `session_*` in `app/config.py` + `.env.example` + `.env`, and drops now-unused settings (`access_token_expire_minutes`, `refresh_token_expire_days`, `refresh_cookie_path`).

- [x] **9. `feat(backend): add audit logger`**
  - Files: `backend/app/utils/audit.py`
  - Deliverable: `audit(event, **fields)` helper emitting JSON log lines to stdout via stdlib `logging` + `python-json-logger` on a dedicated `audit` logger with `propagate=False`. No rate limiter — rate limiting is deferred to Nginx in phase 6 (auth-decisions §7).

- [x] **10. `feat(backend): add auth schemas and user manager`**
  - Files: `backend/app/schemas/auth.py`, `backend/app/services/user_manager.py`, `backend/app/dependencies.py` (extend)
  - Deliverable: `UserRead` / `UserCreate` / `UserUpdate` subclassing fastapi-users' bases, with `name` / `picture_url` fields and an email validator that trims and lowercases. `UserManager(BaseUserManager[User, UUID])` overrides `validate_password` (length ≥ 12) and emits audit events in `on_after_register` / `on_after_login`. `get_user_db` dependency added alongside `get_db` (wraps the session in `SQLAlchemyUserDatabase(session, User)`).

- [x] **11. `feat(backend): mount fastapi-users auth routers`**
  - Files: `backend/app/routers/auth.py`, `backend/app/routers/users.py`, `backend/app/services/user_manager.py` (extend)
  - Deliverable: split router files by URL prefix — `routers/auth.py` mounts `get_auth_router` (login/logout) and `get_register_router` under `/auth`; `routers/users.py` mounts `get_users_router` under `/users`. The shared `FastAPIUsers[User, UUID]` instance (composed from auth backend + user manager) is added to `services/user_manager.py` alongside the existing `UserManager`, together with `current_user = fastapi_users.current_user(active=True)`. No rate-limiting decorators — nothing custom to wrap.

- [x] **12. `feat(backend): wire auth routers into main`**
  - Files: `backend/app/main.py`
  - Deliverable: both routers (`app.routers.auth`, `app.routers.users`) mounted via `app.include_router(..., prefix="/api")` so the full surface lives under `/api/*` (matching `/api/health`). `/docs` shows all auth endpoints (`POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/users/me`, etc.); `/api/health` still returns 200.

- [x] **13. `test(backend): happy path auth flow`**
  - Files: `backend/tests/test_auth_happy.py`
  - Deliverable: end-to-end test — register → login (captures session cookie) → `GET /api/users/me` (200) → `POST /api/auth/logout` → `GET /api/users/me` (401, cookie cleared).

- [x] **14. `test(backend): auth negative paths`**
  - Files: `backend/tests/test_auth_negative.py`
  - Deliverable: tests cover duplicate email (`400 REGISTER_USER_ALREADY_EXISTS`); wrong password and non-existent email (both `400 LOGIN_BAD_CREDENTIALS` — same response proves no email-exists oracle); password shorter than 12 chars (`400 REGISTER_INVALID_PASSWORD` with our length-policy message); missing or malformed session cookie on `/api/users/me` (`401`). Expired-cookie case is deferred because deterministic testing requires time-mocking or per-test settings overrides; not worth the complexity for marginal coverage.

#### Frontend

Architecture note: this slice's frontend tasks have been rewritten (2026-04-21) to match [frontend-decisions.md](frontend-decisions.md) §§9–12 — loader-based auth via React Router v7 (no Zustand / no context), typed API client via `openapi-typescript` + `openapi-fetch`, Vite dev proxy for same-origin `/api/*`, and `notistack` as the toast surface. UI copy is Spanish (§13).

- [x] **15. `feat(frontend): typed api client, auth loaders and actions, toast provider`**
  - Files: `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/vite.config.ts`, `frontend/.env`, `frontend/.env.example`, `frontend/src/api/client.ts`, `frontend/src/api/schema.d.ts` (generated), `frontend/src/api/types.ts`, `frontend/src/auth/loaders.ts`, `frontend/src/auth/actions.ts`, `frontend/src/main.tsx`
  - Deliverable: `openapi-typescript` (dev) + `openapi-fetch` + `notistack` installed and locked via pnpm. `package.json` gains `"gen:api": "openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts"`; the generated `schema.d.ts` is committed. `apiClient` is a typed `openapi-fetch` wrapper with `credentials: 'include'` and `baseUrl: ''` (same-origin). `rootLoader` calls `apiClient.GET('/api/users/me')` and returns `{ user: data ?? null }` — 401 is an expected pre-login state, not an error. `loginAction`, `registerAction`, `logoutAction` each return either `{ error }` (Spanish copy mapped from the backend's `detail` enum — see slice acceptance) or `redirect(...)` on success. `notistack` `SnackbarProvider` wired in `main.tsx` inside `ThemeProvider` with `maxSnack={3}`, `anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}`. [vite.config.ts](../frontend/vite.config.ts) gains `server.proxy: { '/api': 'http://backend:8000' }` so the dev server serves `/api/*` same-origin; `VITE_API_URL` removed from `.env` / `.env.example` as now-unused. Verification: no client-side auth store exists — `grep -r "localStorage" frontend/src` returns no matches, `grep -rE "AuthStore|Zustand|createContext" frontend/src/auth` returns nothing.

- [x] **16. `feat(frontend): protected route wrapper`**
  - Files: `frontend/src/components/ProtectedRoute.tsx`
  - Deliverable: wrapper reads `useRouteLoaderData('root')`; when `user` is null returns `<Navigate to="/login" replace />`, otherwise renders `children`. No loading state (the root loader resolves before descendants render), no effect hooks, no store access.

- [ ] **17. `feat(frontend): auth layout, login / register / profile pages`**
  - Files: `frontend/src/layouts/AuthLayout.tsx`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/RegisterPage.tsx`, `frontend/src/pages/ProfilePage.tsx`
  - Deliverable: `AuthLayout` is a centred `<Container maxWidth="xs">` with no topbar; it mirrors `ProtectedRoute` — if `useRouteLoaderData('root')` shows an authenticated user, it renders `<Navigate to="/profile" replace />`, otherwise it wraps `<Outlet />`. `LoginPage` / `RegisterPage` use React Router `<Form method="post">` with MUI `<TextField>` (`type="email"`, `type="password"`, `required`, `inputProps={{ minLength: 12 }}` on the password field). Pending state via `useNavigation().state === 'submitting'` (no local `isSubmitting`). Inline field errors via MUI `<Alert severity="error">` driven by `useActionData()`. Error copy is Spanish and maps the backend's `detail` enum: `LOGIN_BAD_CREDENTIALS` → "Email o contraseña inválidos"; `REGISTER_USER_ALREADY_EXISTS` → "Este email ya está registrado"; `REGISTER_INVALID_PASSWORD` → "La contraseña debe tener al menos 12 caracteres"; 429 (future, Nginx-gated) → "Demasiados intentos, inténtalo más tarde". `ProfilePage` reads the user via `useRouteLoaderData('root')` and renders name + email + a logout button — a `<Form method="post" action="/logout">` wrapping an MUI `<Button>`.

- [ ] **18. `feat(frontend): wire auth routes and root loader`**
  - Files: `frontend/src/router.tsx`
  - Deliverable: root route has `id: 'root'`, `loader: rootLoader`, element `<Outlet />`. Two child branches — (a) `<AuthLayout />` containing `/login` (action: `loginAction`) and `/register` (action: `registerAction`); (b) `<ProtectedRoute><RootLayout /></ProtectedRoute>` containing `/` (`HomePage`), `/profile` (`ProfilePage`), and an action-only `/logout` route (action: `logoutAction`, no element). `*` → `<NotFoundPage />` sits outside both branches. Manual verification: `/profile` while anonymous redirects to `/login`; `/login` while authenticated redirects to `/profile`; successful login lands on `/profile`; logout button returns to `/login`.

#### Docs

- [x] **19. `docs(backend): document auth architecture`**
  - Files: `backend/CLAUDE.md`, `backend/.env.example` (final pass)
  - Deliverable: "Auth architecture" section in `backend/CLAUDE.md` cross-referencing [auth-decisions.md](auth-decisions.md) and this slice; `backend/.env.example` confirmed to include every setting introduced in tasks 3 and 8 (session JWT + cookie flags).

---

## Slice 2 — Google OAuth via fastapi-users + httpx-oauth

Cross-ref: decision §12 in [auth-decisions.md](auth-decisions.md) (`oauth_account` join table).

**Acceptance:** clicking "Sign in with Google" on the login page returns the user to the app authenticated, receiving the same single HttpOnly session cookie that email/password login issues. First-time Google users are auto-provisioned with a row in `users` (no password) and a row in `oauth_account`. Returning users match by `(oauth_name, account_id)`. An existing email/password user whose Google email matches can link Google without creating a duplicate account (via fastapi-users' `associate_by_email=True`). OAuth `state` mismatches return 400. All OAuth endpoints are under `/api/auth/google/*`.

### Task plan

#### Backend

- [ ] **1. `chore(backend): add httpx-oauth dependency`**
  - Files: `backend/pyproject.toml`, `backend/uv.lock`
  - Deliverable: `httpx-oauth` declared and locked. `uv sync --locked` passes inside the backend container. fastapi-users is already installed with the `[oauth]` extra so no additional fastapi-users dependency is needed.

- [ ] **2. `feat(backend): add oauth account model and user relationship`**
  - Files: `backend/app/models/oauth_account.py`, `backend/app/models/user.py` (extend), `backend/app/models/__init__.py`
  - Deliverable: `OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID)` in its own module. `User` extended with `oauth_accounts: Mapped[list[OAuthAccount]] = relationship(lazy="joined")` so OAuth rows are loaded eagerly with the user. Both classes re-exported from `models/__init__.py`.

- [ ] **3. `feat(backend): oauth account migration`**
  - Files: `backend/alembic/versions/xxxx_oauth_account.py`
  - Deliverable: migration creates `oauth_account` table with `(oauth_name, account_id)` unique constraint and a foreign key to `users.id` (on delete cascade). `alembic upgrade head` clean on a fresh DB; `alembic downgrade -1` reverts cleanly without touching `users`.

- [ ] **4. `feat(backend): add google oauth settings`**
  - Files: `backend/app/config.py`, `backend/.env.example`, `backend/.env`
  - Deliverable: new settings — `google_client_id`, `google_client_secret`, `google_redirect_uri` (defaults to `http://localhost:8000/api/auth/google/callback` for local dev). `.env.example` documents the expected values and the Google Cloud Console origin.

- [ ] **5. `feat(backend): add google oauth router with associate_by_email`**
  - Files: `backend/app/routers/auth.py` (extend), `backend/app/services/user_manager.py` (extend — pass `oauth_accounts` to `FastAPIUsers` so the built-in OAuth router is available)
  - Deliverable: `GoogleOAuth2(settings.google_client_id, settings.google_client_secret)` instance. Mount `fastapi_users.get_oauth_router(google_client, auth_backend, settings.secret_key, redirect_url=settings.google_redirect_uri, associate_by_email=True)` under `/auth/google` — after main.py's `/api` prefix this becomes `/api/auth/google/{authorize,callback}`. `associate_by_email=True` lets an existing email/password user whose Google email matches link Google without creating a duplicate row.

- [ ] **6. `feat(backend): tag login_ok audit with oauth provider`**
  - Files: `backend/app/services/user_manager.py` (extend `on_after_login`)
  - Deliverable: when `on_after_login` is invoked from an OAuth flow, include `provider="google"` (or equivalent) in the `login_ok` audit event. When invoked from email/password, the field is absent or `"password"`. Keeps the event taxonomy flat (still just `register` + `login_ok` per auth-decisions §10) but lets future analysis filter by provider.

- [ ] **7. `test(backend): google oauth flows`**
  - Files: `backend/tests/test_auth_google.py`
  - Deliverable: mocked-Google tests covering (a) first-time user — row appears in `users` and `oauth_account`, session cookie set; (b) returning user — existing `oauth_account` matched, no duplicate user; (c) email-link — existing email/password user linked to new Google account via `associate_by_email`; (d) state mismatch → 400.

#### Frontend

- [ ] **8. `feat(frontend): sign in with google button`**
  - Files: `frontend/src/pages/LoginPage.tsx` (extend), `frontend/src/pages/RegisterPage.tsx` (extend)
  - Deliverable: MUI button on both pages that navigates to `/api/auth/google/authorize` (full-page navigation — the backend returns a 302 to Google's consent URL). Styled per the Google Brand Guidelines (logo + "Sign in with Google" text).

- [ ] **9. `feat(frontend): oauth callback page`**
  - Files: `frontend/src/pages/OAuthCallbackPage.tsx`, `frontend/src/router.tsx` (extend)
  - Deliverable: page at `/auth/callback` (frontend route, not backend) that calls `AuthStore.bootstrap()` to pick up the session cookie that was set server-side during the Google callback, then redirects to `/profile` on success or `/login` on failure with an error toast.

#### Docs

- [ ] **10. `docs: google oauth setup`**
  - Files: [README.md](../README.md) (extend), `backend/.env.example` (already done in task 4)
  - Deliverable: new "Google OAuth setup" subsection in the root README covering Cloud Console steps (create OAuth consent screen; create OAuth 2.0 Client ID; authorized JavaScript origin `http://localhost:5173`; authorized redirect URI `http://localhost:8000/api/auth/google/callback`), plus where each value goes in `backend/.env`. Linked from the main Quickstart so new contributors find it naturally.

---

## Slice 3 — PWA installable

**Acceptance:** in Chrome desktop/Android, the "Install app" prompt appears on the running app. On iOS Safari, "Add to Home Screen" produces an icon that launches the app full-screen with the correct theme color.

### Task plan

#### Frontend

- [ ] **1. `chore(frontend): add pwa dependencies`**
  - Files: `frontend/package.json`, `frontend/pnpm-lock.yaml`
  - Deliverable: `vite-plugin-pwa` and `workbox-window` installed and locked.

- [ ] **2. `feat(frontend): configure pwa manifest and service worker`**
  - Files: [vite.config.ts](../frontend/vite.config.ts), `frontend/src/main.tsx`
  - Deliverable: `vite-plugin-pwa` configured with manifest fields (`name`, `short_name`, `description`, `theme_color`, `background_color`, `display: standalone`, `start_url: /`). Service worker registered in `main.tsx` with auto-update strategy.

- [ ] **3. `chore(frontend): add pwa icons`**
  - Files: `frontend/public/icon-192.png`, `frontend/public/icon-512.png`, `frontend/public/icon-maskable-512.png`, `frontend/public/apple-touch-icon.png`
  - Deliverable: all four icons generated from a single source SVG. Maskable version follows the safe-zone spec.

- [ ] **4. `feat(frontend): pwa meta tags`**
  - Files: [index.html](../frontend/index.html)
  - Deliverable: `<meta name="theme-color">`, `<link rel="apple-touch-icon">`, and the manifest link tag (injected by vite-plugin-pwa or added manually).

### Verification

- [ ] Chrome DevTools → Application → Manifest: no warnings
- [ ] Chrome Android: install prompt appears
- [ ] iOS Safari: "Add to Home Screen" launches standalone with the correct theme color

---

## Slice 4 — README onboarding in ≤5 commands

**Acceptance:** a fresh clone of the repo produces a working stack following ≤5 shell commands from the root [README.md](../README.md). The Google OAuth setup has its own linked subsection.

### Task plan

#### Docs

- [x] **1. `docs: write root readme`** — completed as part of the slice 1 documentation pass (covered in commit `3f8b4da`). Includes one-paragraph project summary, status table, quickstart, tech stack, monorepo layout, key decisions, and docs index. Links to [PLAN.md](../PLAN.md), [CONTRIBUTING.md](../CONTRIBUTING.md), [DOCKER.md](../DOCKER.md).

- [ ] **2. `docs: add google oauth setup subsection to readme`** — depends on Slice 2 completion; covered by Slice 2 task 10. Listed here for completeness.

- [ ] **3. Sanity-check onboarding on a fresh clone**
  - Clone the repo to a temporary directory, follow the README Quickstart verbatim, confirm `http://localhost:5173` shows the working app after ≤5 commands. Fix any drift.

---

## Suggested order

1. **Slice 1 first** — it's the backbone; Slice 2 builds on its schema, `AuthStore`, and router structure
2. **Slice 2** — adds the `oauth_account` table and reuses the single-cookie auth backend plus the Slice 1 `AuthStore`
3. **Slice 3 in parallel with Slice 2** if blocked (independent of backend)
4. **Slice 4 last** — by then the real commands and Google OAuth setup are stable
