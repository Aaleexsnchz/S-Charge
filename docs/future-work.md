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

**Complete auth audit coverage.** Slice 1 audits `register` and `login_ok` via `UserManager` hooks — the two events fastapi-users exposes natively. `login_fail` and `logout` have no native hooks: `login_fail` needs a FastAPI exception handler matching `ErrorCode.LOGIN_BAD_CREDENTIALS` on the router's 400 responses; `logout` needs a thin wrapper around `CookieTransport.get_logout_response()` to emit the event before returning. Roughly 20–25 lines of custom code total. Deferred because there's no log aggregator consuming these events at thesis scale — the coverage gain is operationally invisible until a real deployment. Trigger: a security incident or support scenario where the gap becomes actionable (e.g., "show me failed login attempts for this account", "verify this user logged out cleanly"). Rationale: [auth-decisions §10](auth-decisions.md).

**Cleanup of stale unverified accounts.** Slice 3 introduces email verification but the rows themselves are never deleted — a user who registers and never clicks the verify link leaves an `is_verified=False` row indefinitely, and re-registration with the same email returns `REGISTER_USER_ALREADY_EXISTS`. At thesis scale this is harmless (no abuse vector, no storage pressure). Production hygiene wants a periodic job (cron or APScheduler in-process) that deletes unverified accounts older than N days — typically 7. Trigger: storage of stale rows becoming meaningful, or a legitimate user reporting they can't re-register because of an old typo. Estimated effort: ~30 lines (one query + a scheduler entry).

## Rate limiting beyond Nginx

**Application-level limiter.** Phase 1 defers rate limiting to Nginx `limit_req` ([auth-decisions §7](auth-decisions.md)). Adding slowapi or fastapi-limiter at the app layer would let us count per-user (not only per-IP) and apply limits in dev/test. Trigger: production traffic patterns where per-IP limits are too blunt — shared-office IPs, mobile carrier NAT, or per-user abuse that stays under the per-IP threshold.

## Native mobile client

An iOS/Android version would shift the auth model rather than replace it — the User model, password hashing, validation, and OAuth provider integration stay the same; the transport layer grows additively:

- **Add a second `AuthenticationBackend`** with `BearerTransport` alongside the cookie one. fastapi-users supports multiple backends on the same `FastAPIUsers` instance.
- **Reintroduce refresh tokens** (access + refresh, both stored in iOS Keychain / Android Keystore). The dual-token rationale we rejected for the PWA *does* apply to native clients — no XSS layer, but short-lived access tokens minimise the window where a stolen token is valid.
- **OAuth via the system browser** (ASWebAuthenticationSession on iOS, Custom Tabs on Android) with a deep-link callback. PKCE becomes required (public client, no backend-held secret).
- **CSRF concerns vanish** for the bearer path — bearer headers are not sent automatically by the OS.

Trigger: concrete ask from supervisor or stakeholder, or an explicit post-thesis expansion. Estimated backend effort: 2–3 days (second backend + refresh endpoint); mobile effort is the usual per-platform work on top.

## Live CPO integration (replacing the REVE seed)

Phase 2 seeds Spanish charging-network data from REVE's public API once and treats it as a static snapshot — the 5-requests-per-hour cap on the REVE external API makes a live mirror impractical, and relaying CPO commercial data without an agreement is academically dubious for a publicly-deployed thesis demo. The thesis ships with that limitation flagged honestly in [PLAN.md](../PLAN.md)'s *Mocked / Simplified* table.

The schema is already aligned with **OCPI 2.2.1** (the European Open Charge Point Interface standard) — `party_id`, `evse_id`, IEC 62196 connector standards. Adding a real-time data source is therefore a config change, not a schema migration: extend the `charging_points.source` enum (currently `reve_seed` | `user`) with a per-CPO value (e.g. `cpo_iberdrola`, `cpo_endesax`, `cpo_ionity`) and add a per-source ingest job. The map, filters, detail page, and tariff display all consume the same DB columns regardless of source.

Possible production data sources, ranked by likely accessibility:

- **REVE commercial API tier.** If REVE offers a paid plan with a higher rate limit, the existing seed script becomes a periodic delta-sync job (the spec already supports `date_from`, `only_dynamic_info`, pagination — see [docs/phase-2.md](phase-2.md)).
- **Direct OCPI agreements with individual CPOs** (Iberdrola, Endesa X, IONITY, Repsol, etc.). Each CPO that publishes an OCPI-compatible endpoint can be onboarded with a credential block + a per-source ingest job, no schema change.
- **EU Data Act §7 charging-point data sharing**, once national implementation lands in Spain. The Data Act mandates real-time charging-point availability sharing for commercial CPOs above a threshold; once enforcement is operational, this becomes the obvious primary source.

Trigger: a thesis-defense follow-up project, a real-deployment ask from the supervisor, or a research collaboration that needs live data. Estimated backend effort once a source is identified: 1–2 days for the per-source ingest job, plus the operational overhead of credentials and rate-limit handling per CPO.

## Daily REVE refresh + admin tariff editor

Phase 2 originally planned an in-process `AsyncIOScheduler` running a daily 04:00 Europe/Madrid job to refresh `/connectors/tariffs` (and, optionally, `/evses/operational_status`). Both tasks were dropped after the first real `/cpos` call confirmed REVE is registry-scale: a daily nationwide refresh of `/connectors/tariffs` (~600 pages at 100/page) doesn't fit the 5 req/hr public-API cap. The initial cursor-driven seed snapshots tariffs once; they are **static thereafter** until manually updated.

Two deferred deliverables:

- **Automated refresh.** Once the cap is lifted (commercial REVE tier, OCPI agreements, or EU Data Act §7 — see *Live CPO integration* above), reintroduce the in-process scheduler. The `apscheduler` dependency is already in `pyproject.toml` and the cursor table can carry the `last_attempted_at` watermark for delta `date_from` queries.
- **Admin tariff editor.** Until automation lands, an admin can manually `UPDATE tariffs SET price_per_kwh = ... WHERE id = ...` via psql. A future-work item is a small admin UI (auth-gated route, list of tariffs with inline edit, audit log entry per change). Estimated effort: 2–3 days for the route + the UI.

Trigger: same as *Live CPO integration*, or a user complaint that a price is wrong.

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

## Developer experience

**Extract reusable skill: FastAPI-users auth for SPAs/PWAs.** [auth-decisions.md](auth-decisions.md), the slice 1 code, and the test fixtures together form a niche-but-complete pattern — single HttpOnly cookie (no refresh tokens for same-origin PWAs), pwdlib-backed Argon2 at OWASP minimums, citext email with `TYPE_CHECKING` override, alembic-driven test schema with transactional rollback, library-native error-code contract. Worth packaging as a Claude Code skill if ever starting another FastAPI project so the decisions don't have to be re-derived. Trigger: starting a second FastAPI project, or finding a credible skill-sharing platform worth uploading to. Estimated effort once triggered: 3–5 hours to extract, test the skill against a throwaway project, and refine.
