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

- [x] **17. `feat(frontend): auth layout, login / register / profile pages`**
  - Files: `frontend/src/layouts/AuthLayout.tsx`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/RegisterPage.tsx`, `frontend/src/pages/ProfilePage.tsx`
  - Deliverable: `AuthLayout` is a centred `<Container maxWidth="xs">` with no topbar; it mirrors `ProtectedRoute` — if `useRouteLoaderData('root')` shows an authenticated user, it renders `<Navigate to="/profile" replace />`, otherwise it wraps `<Outlet />`. `LoginPage` / `RegisterPage` use React Router `<Form method="post">` with MUI `<TextField>` (`type="email"`, `type="password"`, `required`, `inputProps={{ minLength: 12 }}` on the password field). Pending state via `useNavigation().state === 'submitting'` (no local `isSubmitting`). Inline field errors via MUI `<Alert severity="error">` driven by `useActionData()`. Error copy is Spanish and maps the backend's `detail` enum: `LOGIN_BAD_CREDENTIALS` → "Email o contraseña inválidos"; `REGISTER_USER_ALREADY_EXISTS` → "Este email ya está registrado"; `REGISTER_INVALID_PASSWORD` → "La contraseña debe tener al menos 12 caracteres"; 429 (future, Nginx-gated) → "Demasiados intentos, inténtalo más tarde". `ProfilePage` reads the user via `useRouteLoaderData('root')` and renders name + email + a logout button — a `<Form method="post" action="/logout">` wrapping an MUI `<Button>`.

- [x] **18. `feat(frontend): wire auth routes and root loader`**
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

**Known limitation — addressed in Slice 3.** `associate_by_email=True` combined with unverified password registration opens a pre-registration shell attack: an attacker registers a password account with the victim's email, waits for the victim to sign in with Google, and the accounts auto-link — the attacker can then use the password they chose. Slice 3 closes this by gating password login on email verification (`requires_verification=True`) and marking Google-issued accounts as verified by default (`is_verified_by_default=True`). Until Slice 3 ships, this demo-only auth flow is not safe against a targeted attacker.

### Task plan

#### Backend

- [x] **1. ~~`chore(backend): add httpx-oauth dependency`~~** — no-op on 2026-04-24: slice 1's `fastapi-users[oauth]` extra already installs `httpx-oauth 0.16.1`. Verified via `docker compose exec backend uv pip list`. No files touched, no commit.

- [ ] **2. `feat(backend): add oauth account model and user relationship`**
  - Files: `backend/app/models/user.py` (extend), `backend/app/models/__init__.py`, `backend/app/dependencies.py` (extend)
  - Deliverable: `OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID)` added to `models/user.py` (same aggregate as `User`, per [backend/CLAUDE.md](../backend/CLAUDE.md)'s "one file per aggregate") with a `user_id` override that points the foreign key at `users.id` — fastapi-users' mixin hardcodes `ForeignKey("user.id")` which doesn't match our pluralised table name. `User` extended with `oauth_accounts: Mapped[list[OAuthAccount]] = relationship(lazy="joined")` so OAuth rows are loaded eagerly with the user. `OAuthAccount` exported from `models/__init__.py`. `get_user_db` in `app/dependencies.py` now passes `OAuthAccount` as the third arg to `SQLAlchemyUserDatabase(session, User, OAuthAccount)` so `user_manager.oauth_callback` can upsert rows — `FastAPIUsers[...]` itself doesn't need extra args.

- [ ] **3. `feat(backend): oauth account migration`**
  - Files: `backend/alembic/versions/xxxx_oauth_account.py`
  - Deliverable: migration creates `oauth_account` table with `(oauth_name, account_id)` unique constraint and a foreign key to `users.id` (on delete cascade). `alembic upgrade head` clean on a fresh DB; `alembic downgrade -1` reverts cleanly without touching `users`.

- [ ] **4. `feat(backend): add google oauth settings`**
  - Files: `backend/app/config.py`, `backend/.env.example`, `backend/.env`
  - Deliverable: new settings — `google_client_id`, `google_client_secret`, `google_redirect_uri` (defaults to `http://localhost:5173/api/auth/google/callback` — the Vite dev origin, so the session cookie lands on `:5173` where the SPA runs; pointing Google directly at `:8000` would set the cookie on the wrong origin and break subsequent same-origin `/api/*` calls from `:5173`). `.env.example` documents the expected values and the Google Cloud Console "Authorised redirect URIs" entry.

- [ ] **5. `feat(backend): add google oauth router with redirect transport`**
  - Files: `backend/app/utils/auth_backend.py` (extend), `backend/app/routers/auth.py` (extend), `backend/app/services/user_manager.py` (extend — pass `[auth_backend]` plus the `oauth_client` and `oauth_accounts` schema to `FastAPIUsers` so `get_oauth_router` is available), `backend/app/main.py` (extend — exception handler)
  - Deliverable:
    1. **`CookieRedirectTransport(CookieTransport)`** in `auth_backend.py` overrides `get_login_response` to return `303 See Other → /profile` while still attaching the session cookie via `_set_login_cookie`. Rationale is captured in a short docstring: fastapi-users' stock `CookieTransport` returns `204 No Content`, which leaves a top-level browser navigation (Google → our callback) on a blank page; a server-side 303 avoids that without needing a popup-based frontend flow (relevant because slice 4 makes this a PWA where popup UX is weakest on iOS installed apps).
    2. **`oauth_backend = AuthenticationBackend(name="oauth-cookie", transport=CookieRedirectTransport(...), get_strategy=get_jwt_strategy)`** composed alongside the existing `auth_backend`. Same JWT strategy, same cookie name / flags — sessions set by either backend are read by the same `current_user` dependency. `oauth_backend` is **not** registered with `FastAPIUsers([...])`; it's used only to satisfy `get_oauth_router`'s `backend` parameter.
    3. **Google client**: `google_client = GoogleOAuth2(settings.google_client_id, settings.google_client_secret)`.
    4. **Router mount**: `fastapi_users.get_oauth_router(google_client, oauth_backend, settings.secret_key, redirect_url=settings.google_redirect_uri, associate_by_email=True)` under `/auth/google` (after main.py's `/api` prefix: `/api/auth/google/{authorize,callback}`). `associate_by_email=True` lets an existing email/password user whose Google email matches link Google without creating a duplicate row.
    5. **Error redirect**: an exception handler registered on the FastAPI app maps `HTTPException`s raised by the callback (`OAUTH_INVALID_STATE`, `OAUTH_USER_ALREADY_EXISTS`, `OAUTH_NOT_AVAILABLE_EMAIL`, `ACCESS_TOKEN_DECODE_ERROR`, `ACCESS_TOKEN_ALREADY_EXPIRED`, `LOGIN_BAD_CREDENTIALS`) — scoped to requests under `/api/auth/google/*` only — to `303 → /login?error=oauth_failed`, so the browser always lands back in the SPA instead of on a raw JSON error page. Email/password error responses are untouched.

- [ ] **6. `feat(backend): tag login_ok audit with oauth provider`**
  - Files: `backend/app/services/user_manager.py` (extend `on_after_login`)
  - Deliverable: when `on_after_login` is invoked from an OAuth flow, include `provider="google"` (or equivalent) in the `login_ok` audit event. When invoked from email/password, the field is absent or `"password"`. Keeps the event taxonomy flat (still just `register` + `login_ok` per auth-decisions §10) but lets future analysis filter by provider.

- [ ] **7. `test(backend): google oauth flows`**
  - Files: `backend/tests/test_auth_google.py`
  - Deliverable: mocked-Google tests covering (a) first-time user — row appears in `users` and `oauth_account`, session cookie set; (b) returning user — existing `oauth_account` matched, no duplicate user; (c) email-link — existing email/password user linked to new Google account via `associate_by_email`; (d) state mismatch → 400.

#### Frontend

- [x] **8. `feat(frontend): sign in with google button`**
  - Files: `frontend/src/pages/LoginPage.tsx` (extend), `frontend/src/pages/RegisterPage.tsx` (extend)
  - Deliverable: MUI button on both pages styled per Google brand guidelines (G logo + "Iniciar sesión con Google"). `/authorize` returns JSON `{ authorization_url }` (plus the CSRF cookie the library uses for state validation), not a redirect — so the click handler is: `const { data } = await apiClient.GET('/api/auth/google/authorize')` → `window.location.href = data.authorization_url`. On success, Google → backend callback → 303 to `/profile` → root loader re-runs and renders the authenticated shell. On failure, the backend 303s to `/login?error=oauth_failed`; `LoginPage` reads `searchParams.get('error')` on mount and shows a notistack toast ("No se pudo iniciar sesión con Google. Inténtalo de nuevo."), then clears the param via `setSearchParams({})` so a reload doesn't re-fire the toast.

- [x] **9. ~~`feat(frontend): oauth callback page`~~** — removed on 2026-04-24. Task 5's `CookieRedirectTransport` already 303s the browser from `/api/auth/google/callback` directly to `/profile`, at which point the root loader rehydrates from the session cookie. No client-side callback page is needed; the slice 1 refactor to loader-based auth also removed `AuthStore.bootstrap()` which the original task referenced.

#### Docs

- [x] **10. `docs: google oauth setup`**
  - Files: [README.md](../README.md) (extend), `backend/.env.example` (already done in task 4)
  - Deliverable: new "Google OAuth setup" subsection in the root README covering Cloud Console steps (create OAuth consent screen; create OAuth 2.0 Client ID; authorised JavaScript origin `http://localhost:5173`; authorised redirect URI `http://localhost:5173/api/auth/google/callback` — matching the Vite-proxied same-origin flow, see task 4), plus where each value goes in `backend/.env`. Linked from the main Quickstart so new contributors find it naturally.

---

## Slice 3 — Email verification and password reset

**Motivation.** Slice 2 ships OAuth with `associate_by_email=True`, which (by itself) is vulnerable to the pre-registration shell attack noted there. The fix is email verification on password registration + auto-verification for OAuth users. Password reset is bundled in the same slice because OAuth-first users (who never set a password) need it to bootstrap the email/password path on their own account — fastapi-users' `oauth_callback` generates a random password hash and discards the plaintext, so the user never learns it.

**Acceptance:**

- Registering with email/password creates the user with `is_verified=False`, sends a verification email, and returns 201 — but subsequent `POST /api/auth/login` is rejected with `LOGIN_USER_NOT_VERIFIED` until the link is clicked.
- Clicking the verification link lands the browser on the SPA's verify page, which calls `POST /api/auth/verify?token=...`, flips `is_verified=True`, and shows a success toast.
- Registering with Google OAuth auto-provisions the user with `is_verified=True` (no email sent).
- A verified user who forgets their password can request a reset email and set a new password via the token in the email.
- An OAuth-first user can use the same reset flow to set an email/password on their account (the reset email arrives because their email is already verified).
- Duplicate-email registration returns the same `400 REGISTER_USER_ALREADY_EXISTS` response as today — no enumeration.
- Email sends failing in local dev don't crash the flow (log the error, keep the registration — Resend's sandbox domain is used for dev, see task 2).

**Locked decisions** (to be appended to [auth-decisions.md](auth-decisions.md))

- Email provider: **Resend** via the `resend` Python SDK. 100 emails/day free, simple API, supports a sandbox domain for local dev without DNS setup. Chosen over SMTP to avoid dealing with SPF/DKIM during phase 1; those come back when we own the production domain in phase 6.
- Verification token: fastapi-users default (JWT, 1h lifetime, signed with `secret_key`).
- Reset token: fastapi-users default (JWT, 1h lifetime, signed with `secret_key`).
- Password login is gated via `requires_verification=True` on the auth router.
- OAuth is auto-verified via `is_verified_by_default=True` on the OAuth router.
- No separate email-verification state table — fastapi-users' `is_verified` boolean on `users` is sufficient for slice scope. Tokens are stateless JWTs (no server-side revocation); acceptable for the 1h lifetime.

### Task plan

#### Backend

- [x] **1. `chore(backend): add resend dependency`**
  - Files: `backend/pyproject.toml`, `backend/uv.lock`
  - Deliverable: `resend` declared and locked. `uv sync --locked` passes.

- [x] **2. `feat(backend): add email settings`**
  - Files: `backend/app/config.py`, `backend/.env.example`, `backend/.env`
  - Deliverable: new settings — `resend_api_key` (empty default so import-time doesn't fail), `mail_from` (e.g., `noreply@tfm.example.com`; for dev, Resend's `onboarding@resend.dev` sandbox works), `app_base_url` (e.g., `http://localhost:5173`; the reset/verify emails need the absolute frontend URL).

- [x] **3. `feat(backend): email helper service`**
  - Files: `backend/app/services/email.py`, `backend/tests/test_services_email.py`
  - Deliverable: `send_verification_email(to, token)` and `send_reset_password_email(to, token)`. Both build an absolute URL (`settings.app_base_url + "/verify?token=" + token`, likewise for reset) and call `resend.Emails.send(...)`. Plain-text emails for slice scope; HTML polish deferred. Send failures are logged via the audit helper (new events `email_send_ok` / `email_send_failed`) and **do not raise** — a transient Resend outage shouldn't crash a registration. Tests mock the Resend SDK.

- [x] **4. `feat(backend): wire user_manager verification and reset hooks`**
  - Files: `backend/app/services/user_manager.py` (extend)
  - Deliverable: `on_after_register` continues to audit, then calls `self.request_verify(user, request)` so fastapi-users issues a token and invokes `on_after_request_verify`. `on_after_request_verify` calls `send_verification_email`. `on_after_forgot_password` calls `send_reset_password_email`. `on_after_verify` and `on_after_reset_password` audit `verify_ok` and `reset_ok` respectively. All hooks accept `request` for IP/UA auditing.

- [x] **5. `feat(backend): mount verify + reset routers, gate login, verify oauth by default`**
  - Files: `backend/app/routers/auth.py` (extend)
  - Deliverable: mount `fastapi_users.get_verify_router(UserRead)` and `fastapi_users.get_reset_password_router()` under `/auth`. Change `get_auth_router(auth_backend)` → `get_auth_router(auth_backend, requires_verification=True)` so unverified password users get `400 LOGIN_USER_NOT_VERIFIED` instead of a session cookie. Change the Google OAuth mount to pass `is_verified_by_default=True` so Google-sourced accounts skip verification.

- [x] **6. `test(backend): verification and reset flows`**
  - Files: `backend/tests/test_auth_verify.py`, `backend/tests/test_auth_reset.py`, `backend/tests/test_auth_negative.py` (extend)
  - Deliverable:
    - Verify flow: register → `POST /api/auth/login` fails `LOGIN_USER_NOT_VERIFIED` → extract token from the mocked Resend call → `POST /api/auth/verify {token}` returns 200 → login now succeeds.
    - Reset flow: for a verified user, `POST /api/auth/forgot-password {email}` returns 202 regardless of whether the email exists (no enumeration) → extract token from mocked send → `POST /api/auth/reset-password {token, password}` → login with new password.
    - OAuth verify-by-default: mocked Google callback creates a user with `is_verified=True` (DB assertion).
    - Negative: expired / tampered verify token returns 400; reset with short password returns 400 `RESET_PASSWORD_INVALID_PASSWORD`.

#### Frontend

- [x] **7. `feat(frontend): "revisa tu email" screen after register`**
  - Files: `frontend/src/pages/CheckEmailPage.tsx`, `frontend/src/auth/actions.ts` (`registerAction` update), `frontend/src/router.tsx`
  - Deliverable: `registerAction` now redirects to `/verificar-email-pendiente` (Spanish, per frontend-decisions §13) on 201 instead of logging the user in. The page reads the email from URL state / session storage and shows "Te hemos enviado un enlace a {email}" with a "Reenviar correo" button that POSTs `/api/auth/request-verify-token`.

- [x] **8. `feat(frontend): verification landing page`**
  - Files: `frontend/src/pages/VerifyEmailPage.tsx`, router wire
  - Deliverable: `/verificar-email?token=...` POSTs to `/api/auth/verify` on mount (one-shot, so using `useEffect` with a ref-based guard to avoid React 18 strict-mode double-invoke). On success: success toast + redirect to `/login`. On failure: error toast + redirect to `/login?error=verify_failed`.

- [x] **9. `feat(frontend): forgot-password form`**
  - Files: `frontend/src/pages/ForgotPasswordPage.tsx`, link from LoginPage
  - Deliverable: `/olvide-contrasena` form with email field. Calls `/api/auth/forgot-password`. Regardless of backend response (202 either way), always shows "Si existe una cuenta con ese email, recibirás un enlace" to avoid enumeration.

- [x] **10. `feat(frontend): reset password form`**
  - Files: `frontend/src/pages/ResetPasswordPage.tsx`, router wire
  - Deliverable: `/restablecer-contrasena?token=...` with new-password field (`minLength=12` client-side). Calls `/api/auth/reset-password`. On success: toast "Contraseña actualizada" + redirect to `/login`. On 400 with `RESET_PASSWORD_BAD_TOKEN`: "Enlace inválido o expirado" with a "Solicitar otro" link.

- [x] **11. `feat(frontend): handle LOGIN_USER_NOT_VERIFIED on login`**
  - Files: `frontend/src/pages/LoginPage.tsx` (extend), `frontend/src/auth/actions.ts` (`loginAction` update)
  - Deliverable: when `loginAction` sees `LOGIN_USER_NOT_VERIFIED`, return a typed error that LoginPage renders as "Verifica tu email antes de iniciar sesión. ¿Reenviar?" with a button that POSTs `/api/auth/request-verify-token` for the entered email. The button rate-limiting is delegated to Nginx (phase 6) — frontend doesn't add its own.

#### Docs

- [x] **12. `docs: record email verification decisions`**
  - Files: [docs/auth-decisions.md](auth-decisions.md), [docs/future-work.md](future-work.md)
  - Deliverable: append a dated section to `auth-decisions.md` covering: provider choice (Resend), rationale vs SMTP, `requires_verification=True` + `is_verified_by_default=True` decision, token lifetimes, and the slice 2 → slice 3 handoff. *(Note: there was no existing "email verification" entry in `future-work.md` to remove; instead, this commit adds a "Cleanup of stale unverified accounts" follow-up that surfaced during slice 3.)*

- [x] **13. `docs: update README with email provider setup`**
  - Files: [README.md](../README.md)
  - Deliverable: new "Email provider setup" subsection covering Resend account creation, API-key env var, sandbox-domain note (for dev without a verified domain), and production setup (verify your domain in Resend, add SPF/DKIM DNS records) to be run in phase 6.

---

## Slice 4 — PWA installable

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

## Slice 5 — README onboarding in ≤5 commands

**Acceptance:** a fresh clone of the repo produces a working stack following ≤5 shell commands from the root [README.md](../README.md). The Google OAuth setup has its own linked subsection.

### Task plan

#### Docs

- [x] **1. `docs: write root readme`** — completed as part of the slice 1 documentation pass (covered in commit `3f8b4da`). Includes one-paragraph project summary, status table, quickstart, tech stack, monorepo layout, key decisions, and docs index. Links to [PLAN.md](../PLAN.md), [CONTRIBUTING.md](../CONTRIBUTING.md), [DOCKER.md](../DOCKER.md).

- [ ] **2. `docs: add google oauth setup subsection to readme`** — depends on Slice 2 completion; covered by Slice 2 task 10. Listed here for completeness.

- [ ] **3. Sanity-check onboarding on a fresh clone**
  - Clone the repo to a temporary directory, follow the README Quickstart verbatim, confirm `http://localhost:5173` shows the working app after ≤5 commands. Fix any drift.

---

## Suggested order

1. **Slice 1 first** — it's the backbone; everything else builds on its schema, auth backend, and router structure.
2. **Slice 2** — adds the `oauth_account` table and reuses the single-cookie auth backend. Ships with a documented security gap (pre-registration shell attack) that Slice 3 closes.
3. **Slice 3** — email verification + password reset. Closes Slice 2's gap and completes the auth flow. Must land before any production deploy.
4. **Slice 4 in parallel with Slice 2 or 3** if needed (PWA work is independent of backend auth changes).
5. **Slice 5 last** — by then the real commands, Google OAuth setup, and email provider setup are stable enough to document without drift.
