# Future work

Items deliberately out of scope for the TFM, tracked so they're traceable rather than invisible. Each entry: *what*, *why deferred*, *what would trigger revisiting*. Add new items here as they come up.

Cross-refs: [auth-decisions.md](auth-decisions.md) has fuller rationale for auth-adjacent items; [../PLAN.md](../PLAN.md) lists what's mocked for thesis scope.

---

## Auth hardening

**DB-backed session revocation.** Replace the stateless session JWT with a `sessions` table so logout revokes server-side. Deferred on scope grounds — the thesis contribution lies in phases 3–4. Trigger: need for "log out of all devices" or any compliance requirement for session invalidation. Full rationale: [auth-decisions §6](auth-decisions.md).

**Per-account lockout.** Lock an account for N minutes after K failed logins — canonical complement to per-IP rate limiting (OWASP ASVS V2.2.5). Requires `failed_login_attempts` and `locked_until` columns plus a hook into the authentication path. Trigger: deploying to general internet traffic, or credential-stuffing attempts visible in logs. Rationale: [auth-decisions §8](auth-decisions.md).

**Persisted audit events.** Move the JSON stdout audit logs into an `auth_events` table for per-user activity queries and append-only guarantees. Trigger: compliance ask (PCI-DSS §10.2, SOC 2 CC7.2) or a support flow needing user history. Rationale: [auth-decisions §10](auth-decisions.md).

**HIBP k-anonymity password check.** Reject passwords known to be in breach corpora via the Pwned Passwords API (one pseudonymous call per password set). Deferred because the external dependency complicates tests. Trigger: observed correlation between breach-notification emails and local registrations. Rationale: [auth-decisions §11](auth-decisions.md).

**Sliding session expiration.** The current design ([auth-decisions §5](auth-decisions.md), `session_token_expire_days=14`) hard-expires every session at 14 days regardless of activity — users must re-login on schedule. Sliding expiration resets the clock on each authenticated request (middleware that re-mints the JWT and re-sets the cookie when the token is past half its lifetime), matching the UX of Gmail, GitHub, Discord, Netflix. Deferred because a thesis demo is reviewed in short bursts where hard expiry isn't noticeable. Trigger: real users complaining about unexpected logouts, or "real app feel" becoming a hard requirement. Estimated effort: ~15 lines of middleware, no DB changes.

## Rate limiting beyond Nginx

**Application-level limiter.** Phase 1 defers rate limiting to Nginx `limit_req` ([auth-decisions §7](auth-decisions.md)). Adding slowapi or fastapi-limiter at the app layer would let us count per-user (not only per-IP) and apply limits in dev/test. Trigger: production traffic patterns where per-IP limits are too blunt — shared-office IPs, mobile carrier NAT, or per-user abuse that stays under the per-IP threshold.

## Native mobile client

An iOS/Android version would shift the auth model rather than replace it — the User model, password hashing, validation, and OAuth provider integration stay the same; the transport layer grows additively:

- **Add a second `AuthenticationBackend`** with `BearerTransport` alongside the cookie one. fastapi-users supports multiple backends on the same `FastAPIUsers` instance.
- **Reintroduce refresh tokens** (access + refresh, both stored in iOS Keychain / Android Keystore). The dual-token rationale we rejected for the PWA *does* apply to native clients — no XSS layer, but short-lived access tokens minimise the window where a stolen token is valid.
- **OAuth via the system browser** (ASWebAuthenticationSession on iOS, Custom Tabs on Android) with a deep-link callback. PKCE becomes required (public client, no backend-held secret).
- **CSRF concerns vanish** for the bearer path — bearer headers are not sent automatically by the OS.

Trigger: concrete ask from supervisor or stakeholder, or an explicit post-thesis expansion. Estimated backend effort: 2–3 days (second backend + refresh endpoint); mobile effort is the usual per-platform work on top.

## Programmatic API for non-browser clients

**API-key bearer backend.** Researchers or scripts querying the simulation output (phases 3–4) via curl can't use the session cookie. A `/api/v1/` namespace with its own bearer-token `AuthenticationBackend` and an API-key management UI would fill that gap without touching the PWA auth. Trigger: first external programmatic query, or reproducibility tooling requested by a paper reviewer.

## Business features mocked in thesis

Per [../PLAN.md](../PLAN.md), these are intentionally simulated — the thesis contribution is simulation and algorithm work, not payment rails or device integration.

**Real payments.** Stripe or similar for user-paid charging sessions. Currently a mocked service returning success. PCI-DSS scope argues for a Stripe-Elements-style capture so the backend never touches card data.

**Commission payouts.** Stripe Connect or equivalent for private-point owners. Currently mocked. Requires KYC, tax forms, and country-specific reporting — production-grade compliance work.

**Real-time occupation for private points.** Currently a deterministic simulated schedule. Real integration would need device telemetry (OCPP for commercial hardware, or similar for consumer devices) feeding a pub/sub layer the frontend subscribes to.

## Observability and ops

**Structured log aggregation.** stdout JSON logs end up in Docker's local buffer. Production-grade: ship to Loki + Grafana, Datadog, or similar. Trigger: more than one instance, or needing cross-timeframe log search.

**Metrics and alerting.** Prometheus + Grafana, or a hosted equivalent. At thesis scale (single VPS, no real users) there is nothing to alert on. Trigger: first external users, or any SLO commitment.

**Horizontal scaling.** The stateless session JWT scales horizontally trivially; any future in-memory state (app-level rate limiter, in-process caches) would need Redis. The `DATABASE_URL` pool is already sized for concurrent workers. Trigger: load measurements saturating a single Uvicorn worker.
