# Authentication

**Status:** ✅ Implemented · **Shipped in** [Phase 1](../phases/phase-1.md)

Email/password and Google sign-in, with email verification and password reset. A single HttpOnly session cookie carries the session; there are no tokens in JavaScript.

## Today

- **Backend** — `/api/auth/*` (`fastapi-users` routers, Argon2id hashing), `/api/auth/google` (`httpx-oauth`), `/api/users/me`. Register, login gated on verification, logout, verify, forgot/reset password. Every auth event emits a JSON audit line to stdout.
- **Rate limits** per client IP and per path, returning `429` with `Retry-After`: 10/minute on login, 10/hour on registration, 5/hour on the endpoints that send mail. Counters are in-process, so they assume a single backend worker.
- **The session gates the whole API.** Everything under `/api` requires it except `/api/health` and `/api/auth/*` — the catalogue, prices, simulator and vehicle list included, since the frontend already required a login for all of them. A test derives the route list from the app and asserts the `401`, so a router mounted unguarded fails the suite rather than shipping open.
- **Frontend** — `features/auth`: login, register, check-email, verify-email, forgot-password, reset-password. Backend error codes are surfaced in Spanish. Auth state is loaded by the React Router root loader.
- Google users are auto-provisioned on first sign-in; an existing email account links Google without duplicating the user.

## Decisions

[auth-0001](../decisions/auth-0001-fastapi-users.md) library choice · [auth-0002](../decisions/auth-0002-cookie-session.md) cookie session, no refresh tokens · [auth-0003](../decisions/auth-0003-preregistration-shell-mitigation.md) pre-registration shell mitigation · [auth-0004](../decisions/auth-0004-rate-limits-and-client-ip.md) rate limits and the audited client IP. Concept chapter: [thesis/autenticacion.md](../thesis/autenticacion.md).

## Pending

- OAuth and email links cannot be tested from a phone in local dev (both point at `localhost`) — they get their real-device test on the production domain in [Phase 5](../phases/phase-5.md).
- The rate limits and the forwarded-header fix only take effect behind Caddy, so neither is verifiable in local dev; both are checked on the first deploy.
