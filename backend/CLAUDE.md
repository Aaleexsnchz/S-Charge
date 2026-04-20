# Backend — FastAPI

See root [CLAUDE.md](../CLAUDE.md) for project orientation and [PLAN.md](../PLAN.md) for roadmap.

## Stack

Python 3.12+, FastAPI, SQLAlchemy 2.0 (async via asyncpg), Alembic, Pydantic v2 + pydantic-settings, Uvicorn, pytest. Package manager: **uv**.

## Layout

```text
backend/
├── app/
│   ├── main.py          FastAPI app factory + router includes
│   ├── config.py        Settings (pydantic-settings, loads backend/.env)
│   ├── database.py      async engine + session factory
│   ├── models/          SQLAlchemy ORM models (one file per aggregate)
│   ├── schemas/         Pydantic request/response models (add as needed)
│   ├── routers/         FastAPI APIRouters (thin — delegate to services)
│   ├── services/        business logic (pure, testable, no FastAPI imports)
│   └── utils/           auth, timezone helpers, etc.
├── alembic/             migrations
├── scripts/             one-off ETL, seed, data generators
└── tests/               pytest (mirrors app/ structure)
```

Routers should be **thin**: parse input, call a service, return. Business logic lives in `services/`, never in route handlers.

## Conventions

### Language-level

- **Python 3.12 features are fine** (match, PEP 695 generics, `Self`).
- File and function naming: **snake_case**.
- Type hints on all public functions and class attributes. Use `from __future__ import annotations` where it simplifies forward refs.
- Prefer pure functions in `services/`. Side effects at the edges (routers, repositories).

### Async

- **Everything I/O is async.** FastAPI endpoints are `async def`. DB sessions are `AsyncSession`. Use `asyncpg` driver (`postgresql+asyncpg://...`).
- Don't mix sync and async SQLAlchemy — pick async end to end.

### SQLAlchemy 2.0

- Declarative with `Mapped[T]` and `mapped_column(...)` — no legacy `Column(...)` style.
- Query via `select(...)` + `session.execute(...)`, not the legacy Query API.
- Relationships: use `relationship()` with typed `Mapped[list["..."]]` annotations.

### Pydantic v2

- `BaseModel` with `ConfigDict(from_attributes=True)` for ORM serialization.
- Validators: `@field_validator`, `@model_validator(mode="after")`.
- Settings via `pydantic-settings` `BaseSettings`, loading from `backend/.env`.

### Alembic

- Always **autogenerate then review** — never trust the diff blindly.
- Migrations run inside the backend container: `docker compose exec backend uv run alembic upgrade head`.
- Never edit applied migrations; add a new one.

### Env and secrets

- All env lives in `backend/.env` (gitignored). Commit `backend/.env.example`.
- Never read `os.environ` directly in code — go through `app.config.settings`.
- Default `DATABASE_URL` in `backend/.env` uses Docker-network hostname (`@db:5432`). For local execution outside Docker, override inline.

### Testing

- pytest in `backend/tests/`, mirroring `app/` structure.
- Service tests are unit tests (no DB). Route tests use a separate test DB or a transactional fixture.
- Run: `uv run pytest` (locally) or `docker compose exec backend uv run pytest`.

### Lint / typecheck

- **Ruff** (`E F I UP B`), line length **100**.
- **MyPy** for type checks.
- Run before commit:

```bash
uv run ruff check app && uv run ruff format --check app && uv run mypy app
```

## Auth architecture

Full rationale in [../docs/auth-decisions.md](../docs/auth-decisions.md); slice 1 task plan in [../docs/phase-1.md](../docs/phase-1.md); scope-deferred items in [../docs/future-work.md](../docs/future-work.md).

**Mechanism.** Single JWT (HS256, 14-day lifetime, audience `tfm:session`) in an HttpOnly cookie — `HttpOnly; Secure; SameSite=Lax`, path `/`. No refresh tokens (PWA-specific rationale in auth-decisions §6). Library: `fastapi-users` + `pwdlib` for Argon2id hashing at OWASP minimums.

**File map.**

```text
app/
├── models/user.py             User model (citext email, name, picture_url)
├── schemas/auth.py            UserRead / UserCreate / UserUpdate + email normaliser
├── services/user_manager.py   UserManager.validate_password + audit hooks;
│                              FastAPIUsers instance + current_user dependency
├── utils/
│   ├── auth_backend.py        CookieTransport + JWTStrategy + AuthenticationBackend
│   ├── security.py            password_helper (Argon2id OWASP params via pwdlib)
│   └── audit.py               audit(event, **fields) — JSON to stdout
├── routers/
│   ├── auth.py                /api/auth/{register,login,logout}
│   └── users.py               /api/users/me + admin CRUD
└── dependencies.py            get_db, get_user_db
```

**In scope (slice 1).** Register, login, logout, `/users/me` via fastapi-users routers. Length-only password policy (≥12 chars). Audit events for `register` and `login_ok`.

**Out of scope (documented in `future-work.md`).** Rate limiting (deferred to Nginx `limit_req` in phase 6), `login_fail` / `logout` audit (no native hooks), refresh tokens, per-account lockout, HIBP password check, DB-backed session revocation.

**Tests.** `tests/test_auth_happy.py` walks register → login → `/users/me` → logout → `/users/me` fails. `tests/test_auth_negative.py` covers duplicate email, bad credentials, short password, missing / malformed cookie.

## Commands

```bash
uv sync --locked --all-groups          # install deps
uv run uvicorn app.main:app --reload   # run locally (needs DATABASE_URL override if DB is in Docker)
uv run alembic revision --autogenerate -m "msg"
uv run alembic upgrade head
uv run pytest
uv run ruff check app
uv run mypy app
```

When running in Docker (the default), see root [DOCKER.md](../DOCKER.md) — `.py` edits auto-reload; `pyproject.toml` changes need a rebuild.
