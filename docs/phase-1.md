# Phase 1 — Foundation

Task breakdown for [PLAN.md](../PLAN.md) Phase 1. Organized as vertical slices: each slice is an independently demoable deliverable with a single acceptance criterion and cross-domain sub-tasks underneath.

## Definition of Done (applies to every slice)

- Migration runs clean from a fresh DB (`alembic upgrade head`)
- Backend: `ruff check` + `mypy` pass; new routes covered by at least one test
- Frontend: `tsc -b` + `eslint` pass; manually exercised in the browser
- `docker compose up` from a clean clone still works end-to-end
- Committed with Conventional Commits (`feat(backend): …`, `feat(frontend): …`, etc.), one logical change per commit

---

## Slice 1 — Email/password auth works end-to-end

**Acceptance:** a new visitor can register, log out, log back in, and a protected `GET /auth/me` returns their user. Invalid credentials return 401. Duplicate email returns 409.

**Backend**
- [ ] Add deps: `passlib[bcrypt]`, `pyjwt`, `email-validator`
- [ ] `User` SQLAlchemy model: `id`, `email` (unique, indexed), `hashed_password` (nullable for future OAuth-only users), `name`, `created_at`
- [ ] Alembic migration for `users` table
- [ ] `core/security.py`: `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`
- [ ] `schemas/auth.py`: `RegisterIn`, `LoginIn`, `TokenOut`, `UserOut`
- [ ] `api/auth.py`: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- [ ] `dependencies.py`: `get_current_user` FastAPI dependency (reads `Authorization: Bearer`)
- [ ] Register the router in `app/main.py`
- [ ] Tests: register → login → `/auth/me` happy path; duplicate email (409); wrong password (401); missing/invalid JWT (401)

**Frontend**
- [ ] `api/client.ts`: fetch wrapper that injects JWT from storage and handles 401 (clear token, redirect to `/login`)
- [ ] `auth/AuthContext.tsx`: token persisted in `localStorage`; exposes `user`, `login`, `register`, `logout`
- [ ] `components/ProtectedRoute.tsx` and wire it into [router.tsx](../frontend/src/router.tsx)
- [ ] `pages/LoginPage.tsx` + `pages/RegisterPage.tsx` (MUI forms, inline error display)
- [ ] Add `/login`, `/register`, `/profile` routes; `/profile` is protected and shows `user` from context

**Infra / docs**
- [ ] Add `JWT_SECRET`, `JWT_EXPIRES_MINUTES` to `backend/.env.example`

---

## Slice 2 — Google OAuth works end-to-end

**Acceptance:** clicking "Sign in with Google" on the login page returns the user to the app authenticated. First-time Google users are auto-provisioned (row created in `users` with `google_sub` set, `hashed_password` null). Returning users match by `google_sub`.

**Backend**
- [ ] Add dep: `authlib` (or `httpx` + manual flow — pick one, document in [backend/CLAUDE.md](../backend/CLAUDE.md))
- [ ] Extend `User` model: `google_sub` (nullable, unique), `picture_url` (optional); migration to add columns
- [ ] `api/auth.py`: `GET /auth/google/login` (builds Google authorize URL, redirects) and `GET /auth/google/callback` (exchanges code, upserts user, returns JWT via redirect to frontend with token in fragment or query)
- [ ] Handle the three cases in the callback: existing `google_sub` → login; existing email, no `google_sub` → link; new user → provision
- [ ] Tests: callback with mocked Google userinfo (new user, existing user, email-link case)

**Frontend**
- [ ] "Sign in with Google" button on `LoginPage` and `RegisterPage` → redirects to `/auth/google/login`
- [ ] Callback landing page (or handler in `AuthContext`) that reads the returned token, stores it, loads `/auth/me`, redirects to `/profile`

**Infra / docs**
- [ ] Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` to `backend/.env.example`
- [ ] Add `VITE_GOOGLE_CLIENT_ID` (if used client-side) to `frontend/.env.example`
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
