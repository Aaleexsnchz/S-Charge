---
title: Authentication
status: draft (thesis writeup, concept-level)
---

# Authentication

Email/password and Google OAuth via [`fastapi-users`](https://fastapi-users.github.io/fastapi-users/) — see [decisions/auth-0001](../decisions/auth-0001-fastapi-users.md) for the library choice. The two places this project deliberately deviates from library defaults are recorded in [decisions/auth-0002](../decisions/auth-0002-cookie-session.md) (session transport) and [decisions/auth-0003](../decisions/auth-0003-preregistration-shell-mitigation.md) (account-linking threat model).

## Identity

UUID v4 primary keys via fastapi-users' `SQLAlchemyBaseUserTableUUID` — non-enumerable, 122 bits of entropy. Emails stored in `citext` (PostgreSQL case-insensitive text), lowercased and trimmed in the Pydantic input schema. The case-insensitive uniqueness invariant lives at the database layer so a buggy code path can't let `Alice@x.com` and `alice@x.com` register as distinct accounts — the underlying account-takeover risk RFC 5321's case-sensitive local part otherwise creates.

## Password storage

Argon2id via [`pwdlib`](https://github.com/frankie567/pwdlib) (the modern successor to `passlib`, bundled with fastapi-users) backed by `argon2-cffi`. OWASP-minimum parameters (`memory_cost=19456`, `time_cost=2`, `parallelism=1`). Auto-rehash on verify lets us tighten the cost parameters later without a migration. Password policy is length-only (≥ 12 characters), aligned with NIST SP 800-63B § 5.1.1 — no composition rules, no forced rotation (both push users toward predictable patterns).

Authentication failures return a single generic `401 "Invalid credentials"` regardless of whether the email exists; fastapi-users runs a dummy hash for the absent-user case so response timing doesn't leak account existence (no user-enumeration oracle).

## Session

A single JWT in an `HttpOnly; Secure; SameSite=Lax` cookie at path `/`, 14-day lifetime, signed HS256 with audience `tfm:session`. No refresh tokens. Composition: `JWTStrategy + CookieTransport` in one `AuthenticationBackend`. The dual-token SPA pattern is deliberately avoided — full rationale in [auth-0002](../decisions/auth-0002-cookie-session.md).

## OAuth (Google)

Provider integration via [`httpx-oauth`](https://github.com/frankie567/httpx-oauth), exposed through fastapi-users' `get_oauth_router`. Provider identities live in a separate `oauth_account` join table (`SQLAlchemyBaseOAuthAccountTableUUID` mixin) with a unique constraint on `(oauth_name, account_id)` — scales to multiple providers without sparse per-provider columns. `associate_by_email=True` lets returning users link Google to their existing password account.

## Email verification and password reset

Password registrations are unverified by default and can't log in until verified (`requires_verification=True` on the auth router). Google OAuth users are auto-verified (`is_verified_by_default=True`) since Google has already proven control of the address. Tokens are fastapi-users' default 1-hour JWTs; delivery is via [Resend](https://resend.com). The combination plus a `UserManager.oauth_callback` override closes the pre-registration shell attack — full rationale in [auth-0003](../decisions/auth-0003-preregistration-shell-mitigation.md).

## Audit logging

JSON-formatted lines on a dedicated `audit` logger to stdout (Docker captures). Events covered today: `register`, `login_ok`, `verify_ok`, `reset_ok`, `email_send_failed`, `oauth_link_reset_password`. Driven by `UserManager` hooks. `login_fail` and `logout` lack native hooks and aren't yet covered.
