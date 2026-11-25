---
id: auth-0001
status: accepted
phase: 1
date: 2026-03
---

# auth-0001: Use `fastapi-users` as the authentication library


**Decision.** Authentication (registration, login, logout, password reset, email verification, Google OAuth, session management) is delegated to [`fastapi-users`](https://fastapi-users.github.io/fastapi-users/) rather than assembled from FastAPI primitives.

**Rationale.** fastapi-users is an actively maintained, opinionated library whose defaults align with current OWASP guidance: UUID primary keys (`SQLAlchemyBaseUserTableUUID`), Argon2id via `pwdlib` + `argon2-cffi`, JWTs with explicit audience claims, and a separate `oauth_account` join table (`SQLAlchemyBaseOAuthAccountTableUUID`). Choosing the library carries those defaults; this project does not re-litigate them as individual ADRs. The two places we deliberately deviate from documented library patterns are recorded separately in [auth-0002](auth-0002-cookie-session.md) (cookie transport, no refresh tokens) and [auth-0003](auth-0003-preregistration-shell-mitigation.md) (account-linking threat model). Building from primitives would mean re-deriving and testing each library default — disproportionate for a thesis whose contribution is the application itself, not its authentication internals.

**Implementation.** Slice 1 onwards. `FastAPIUsers[User, UUID]` instantiated with a custom `UserManager`. One `AuthenticationBackend` composed of `CookieTransport` + `JWTStrategy`. Google OAuth via `httpx-oauth`, mounted with `get_oauth_router`. Per-slice rollout in [plan/phases/phase-1.md](../plan/phases/phase-1.md).

**Rejected alternatives.** FastAPI security utilities + `python-jose` + `argon2-cffi` directly (full control, but every default re-derived and tested by us); [Authlib](https://docs.authlib.org/) (strong on OAuth client/server, weaker on the DB user model); managed identity providers such as Auth0 or [Authentik](https://goauthentik.io/) (extra service to run, breaks the single-VPS infrastructure constraint).

**References.**

- fastapi-users documentation
- `pwdlib`, `httpx-oauth`
- [the thesis](../thesis/S-Charge-TFM.pdf) — concept-level summary of what the library buys us
