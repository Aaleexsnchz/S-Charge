# Authentication Architecture — Decision Record

Background notes for the Phase 1 authentication slice (see [phase-1.md](phase-1.md)). Each entry records a decision, its rationale, how it is realised in the implementation, the alternatives considered and rejected, and primary references suitable for footnoting in the thesis.

## Implementation substrate

Slice 1 is built on top of [fastapi-users](https://fastapi-users.github.io) with PostgreSQL + SQLAlchemy. The library handles the user model scaffolding, register/login/me endpoints, password hashing pipeline, JWT issuance, and (in Slice 2) the OAuth2 social-login flow via [httpx-oauth](https://github.com/frankie567/httpx-oauth). Custom code is added only where the library's defaults don't match the decisions below — chiefly for the refresh-cookie strategy, rate limiting, audit logging, and `citext` email storage. Reinventing the auth pipeline from primitives was considered and rejected as scope inappropriate for a thesis whose contribution lies elsewhere (data integration + simulation + algorithm work).

These decisions are locked for Slice 1. Subsequent changes should be appended as new entries (with date and reason) rather than edited in place.

---

## 1. UUID v4 as primary key for `users`

**Decision.** User IDs are random UUID v4 values generated client-side by Python's `uuid.uuid4()`, not auto-increment integers.

**Rationale.** The user PK is exposed in URLs, JWT `sub` claims, and (later) in shared resources like booking and private-point ownership. Sequential integers leak (a) total user count and growth rate, (b) registration order, and (c) make it trivial to enumerate or guess neighbouring resources by incrementing the ID. UUID v4 has 122 bits of entropy — non-guessable in practice.

**Implementation.** Slice 1. fastapi-users supports UUID primary keys natively via its `SQLAlchemyBaseUserTableUUID` base class, which declares `id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)`. Python-side generation via `uuid.uuid4()` is cryptographically equivalent to PostgreSQL's `gen_random_uuid()` — both draw from the OS CSPRNG (`os.urandom` / `/dev/urandom`). We accept the library default rather than overriding with `server_default=func.gen_random_uuid()` and managing the `pgcrypto` extension; the security claim (122 bits of entropy) is preserved either way.

**Rejected alternatives.** `BIGSERIAL` (smallest, fastest index, but enables enumeration); UUID v7 (time-ordered, better B-tree locality, but PostgreSQL native support landed only in v18 and Python ecosystem support is uneven); Snowflake/KSUID (require an external generator); server-side `gen_random_uuid()` (equivalent security, extra migration complexity for no gain).

**Trade-offs accepted.** 16-byte vs 8-byte index entries and minor B-tree fragmentation due to random insert order. Negligible at thesis-app scale.

**References.**

- RFC 9562 — Universally Unique IDentifiers (UUIDs), §5.4 (v4)
- OWASP ASVS v4.0.3 §V8.3.1 (non-sequential identifiers for sensitive resources)
- Python standard library — `uuid.uuid4` (draws from `os.urandom`)

---

## 2. Email storage with `citext` and normalisation at the schema boundary

**Decision.** Emails are stored in a `citext` column (PostgreSQL extension) and are trimmed and lowercased in the Pydantic input schema before reaching the service layer.

**Rationale.** RFC 5321 §2.3.11 declares the local part of an email technically case-sensitive, but in practice every major mail provider treats it case-insensitively. Storing `Alice@x.com` and `alice@x.com` as distinct accounts would be a UX defect *and* a security defect (account takeover via case-variant registration). `citext` enforces the case-insensitive uniqueness invariant at the database layer, which means a buggy code path cannot bypass it.

**Implementation.** Slice 1. The fastapi-users `email` column is overridden in our custom user model to use `citext` instead of `String`. Alembic migration runs `CREATE EXTENSION IF NOT EXISTS citext` before creating the table.

**Rejected alternatives.** Plain `text` + `lower()` functional unique index (works but breaks ORM ergonomics — every lookup must wrap with `lower()`); lower-on-write in application code only (invariant lives outside the schema, easy to forget).

**References.**

- RFC 5321 §2.3.11 (case sensitivity in mailboxes)
- RFC 5322 (Internet Message Format)
- PostgreSQL documentation — `citext`

---

## 3. Password hashing: Argon2id via `argon2-cffi`

**Decision.** Argon2id is the password hashing algorithm. Implementation via the `argon2-cffi` Python binding using OWASP's minimum recommended parameters: `memory_cost=19456` (19 MiB), `time_cost=2`, `parallelism=1`.

**Rationale.**

- *Algorithm choice.* Argon2id won the Password Hashing Competition (2013–2015) and is OWASP's first-recommended algorithm in the current Password Storage Cheat Sheet. It is **memory-hard** — the memory parameter forces an attacker to commit RAM per guess, which neutralises the GPU/ASIC parallelism advantage that bcrypt, PBKDF2, and scrypt all suffer from to varying degrees.
- *Library choice.* `argon2-cffi` is the canonical Python binding (maintained by Hynek Schlawack — also the author of `attrs` and `structlog`). It has been Django's recommended hasher since version 1.10 (2016) and is widely deployed. The similarly-named `pyargon2` is a separate, much less-used library.
- *Parameters.* OWASP's m=19 MiB / t=2 / p=1 profile takes ~50 ms per hash on a Hetzner CX22 vCPU. Faster than bcrypt cost 12 (~250 ms) while being more secure due to memory-hardness. At our 5/min/IP login rate limit and ~4 GB RAM, contention is not a real constraint.
- *No `passlib`.* `passlib` 1.7.4 is unmaintained (last release 2020) and emits incompatibility warnings against modern hashing-library versions. `argon2-cffi` is used via `pwdlib` — the same author's modern successor to passlib, already bundled with fastapi-users as the default hashing dispatcher.
- *Auto-rehash on verify.* `PasswordHasher.check_needs_rehash()` lets us upgrade existing hashes silently when parameters tighten in future, with no migration needed.

**Implementation.** Slice 1. fastapi-users' default `PasswordHelper` already implements `PasswordHelperProtocol` and delegates to `pwdlib.PasswordHash`. We instantiate it with a custom `Argon2Hasher(memory_cost=19456, time_cost=2, parallelism=1)` to pin OWASP-minimum parameters (tuned down from `argon2-cffi`'s stronger defaults for CX22 login latency). `pwdlib` handles auto-rehash on verify via `argon2-cffi`'s `check_needs_rehash()`. No custom protocol class is needed — five lines in `app/utils/security.py`.

**Rejected alternatives.** bcrypt (mature and safe but CPU-only — no defence against GPU parallelism; chosen historically by reflex but no longer the OWASP first choice); PBKDF2 (faster on GPUs, weaker against ASICs); scrypt (comparable security to bcrypt but less mature Python ecosystem).

**Note on prior version.** An earlier draft of this document selected bcrypt cost 12 with the argument that Argon2id was "ecosystem-immature" and "container-sensitive". Both arguments were weak and the decision was reversed before implementation: `argon2-cffi` is mature production software and the memory parameter is comfortably within container limits at OWASP-recommended profiles.

**References.**

- OWASP Password Storage Cheat Sheet (current revision) — Argon2id parameter recommendations
- Biryukov, Dinu & Khovratovich (2016), *Argon2: New Generation of Memory-Hard Functions for Password Hashing and Other Applications* — original PHC paper
- RFC 9106 — Argon2
- NIST SP 800-63B §5.1.1.2 — Memorized Secret Verifiers
- argon2-cffi documentation, *Choosing Parameters*

---

## 4. JWT (HS256) for access tokens, with explicit `type` claim

**Decision.** Access tokens are JWTs signed with HMAC-SHA-256 (HS256). Standard claims `sub` (user id), `iat`, `exp`, `aud` (audience identifies token purpose; fastapi-users uses `aud` to distinguish access from refresh, equivalent to the `type` claim discussed in earlier drafts). Decoding always pins the algorithm and the expected audience.

**Rationale.**

- *Stateless validation.* The backend can verify tokens without a per-request DB lookup, keeping the hot path cheap.
- *HS256 vs RS256/ES256.* Asymmetric signing is necessary when separate services must verify tokens issued by an auth server. We have a single backend monolith — the asymmetric overhead and key-management complexity are unjustified.
- *Short TTL (15 min).* Limits the blast radius of a leaked access token; pairs with the refresh cookie to give the user a long effective session without long-lived bearer credentials.
- *Pinned algorithm + pinned audience.* Defends against the well-known JWT attack classes: `alg: none` (CVE-2015-9235 family) and key-confusion (using the public key as an HMAC secret). Defends against token-purpose confusion (presenting a refresh token where a bearer is expected).

**Implementation.** Slice 1. Two `JWTStrategy` instances are configured in fastapi-users — one for the access token (15 min, header bearer) with `aud = "users:access"`, and one for the refresh token (14 d, HttpOnly cookie) with `aud = "users:refresh"`. The library refuses tokens whose audience does not match the expected backend.

**Rejected alternatives.** Opaque random session tokens with DB lookup per request (simpler revocation but adds DB load to every authenticated request); PASETO (cleaner crypto story than JWT but a much smaller ecosystem — thesis defensibility cuts both ways and JWT is more standard).

**References.**

- RFC 7519 — JSON Web Token (JWT)
- RFC 7515 — JSON Web Signature, §10.7 (algorithm-confusion attacks)
- RFC 8725 — JWT Best Current Practices
- Sullivan (Auth0, 2015), *Critical vulnerabilities in JSON Web Token libraries*

---

## 5. Token transport: single JWT in an HttpOnly cookie

**Decision.** Authentication state is a single JWT delivered as an `HttpOnly; Secure; SameSite=Lax` cookie at path `/`, with a 14-day lifetime. No separate access/refresh pair. No bearer tokens. No in-memory credential on the client.

**Rationale.**

- *`HttpOnly`.* Cannot be read by JavaScript at all; the token cannot be exfiltrated by XSS. This is the dominant SPA credential-loss vector — `localStorage` / `sessionStorage` tokens are reachable by any script running on the page (including transitive npm dependencies, analytics, embedded widgets). XSS executing in the page can still issue authenticated requests while the page is open, but it cannot persist the credential elsewhere or use it offline.
- *`SameSite=Lax`.* Blocks the cookie from cross-site sub-requests, neutralising most CSRF vectors. Frontend and backend share a single Nginx reverse proxy on the same origin in production; `Lax` is sufficient. `Strict` would interfere with the OAuth callback redirect (Slice 2).
- *`Secure`.* TLS-only transmission in production (overridden to `false` in local dev, where HTTP is the only option).
- *PWA fit.* A PWA is a same-origin web app, not a native mobile app. Its authentication constraints are the constraints of a browser, not of a cross-service OAuth client: one origin, browser-managed cookie jar, service-worker-intercepted fetches that automatically include cookies. A single HttpOnly cookie behaves correctly across every PWA-specific scenario (cold start after the app is closed, service-worker background sync, offline cache with later retry) without any client-side token management.
- *Single long-lived credential.* Our threat model (see §6) does not distinguish "short-lived access token limits blast radius" as a meaningful improvement over "long-lived HttpOnly cookie" for a same-origin SPA: XSS in the page authenticates as the user either way, and HttpOnly prevents exfiltration in both cases. The security posture is equivalent; the operational complexity is not.

**Implementation.** Slice 1. fastapi-users' `CookieTransport` configured with our security flags, composed with a single `JWTStrategy` into one `AuthenticationBackend`. Logout is `CookieTransport.get_logout_response()` (library-provided) which sets `Set-Cookie` with `Max-Age=0` to clear. No custom endpoints.

**Rejected alternatives.** `localStorage` storage (maximum XSS exposure). Dual-token (in-memory access + HttpOnly refresh cookie) — the industry-standard SPA pattern; discussed and rejected in §6 for PWA-specific reasons. Access token in cookie + double-submit CSRF token (viable but adds CSRF infrastructure across every API call — unnecessary when `SameSite=Lax` already addresses the relevant threat).

**References.**

- OWASP ASVS v4.0.3 §V3.4 (Cookie-Based Session Management)
- OWASP Cross-Site Scripting Prevention Cheat Sheet
- OWASP Session Management Cheat Sheet
- MDN Web Docs — *Set-Cookie* (`HttpOnly`, `SameSite`, `Secure` attributes)
- Degges (Auth0, 2018), *Please Stop Using Local Storage* — widely cited industry source on the SPA token-storage debate

---

## 6. Refresh tokens: not used (dual-token pattern rejected for a same-origin PWA)

**Decision.** No refresh tokens. The single HttpOnly cookie (§5) is both the active credential and the long-lived session; there is no `/auth/refresh` endpoint.

**Rationale.** The dual-token dance (short-lived access token in memory + long-lived refresh token in a cookie, with periodic calls to `/auth/refresh`) is the industry-standard SPA pattern. It originated in mobile apps and multi-origin OAuth flows where a bearer token must be presented to a third-party API and the access token cannot be stored in a cookie. For a same-origin monolithic PWA — which is what we are building — the problems the dual-token dance solves are mostly problems we don't have:

- *No third-party API.* The PWA talks only to our own backend. Bearer tokens are not required.
- *"Short access TTL limits blast radius if stolen."* Defeated in practice for SPAs: XSS executing in the page can issue authenticated requests as the user regardless of where the token lives, and `HttpOnly` on a single long-lived cookie prevents exfiltration just as effectively as splitting the credential in two.
- *"Refresh rotation enables revocation."* Not in our threat model — §6 of the previous draft acknowledged that the stateless refresh design cannot revoke an in-flight refresh token before its `exp` either. The long-lived-credential security properties apply whether or not we formally separate access+refresh.
- *PWA cold-start cost.* A memory-only access token is lost when the user closes the PWA window (common for installed PWAs). Every launch then pays for a bootstrap `/auth/refresh` round-trip before any real API call — wasted latency and additional failure surface. A single persistent cookie eliminates this entirely.
- *Service-worker background sync.* A service worker runs in a separate context from the React app and cannot read the in-memory access token. To support background sync with dual-token you would have to stash the token somewhere the service worker can reach (IndexedDB, localStorage), negating the XSS protection that was the whole point. Cookies are sent automatically by the browser, including on fetches replayed by a service worker.

Put plainly: the dual-token pattern is cargo-culted into SPA tutorials from earlier mobile-app architectures, and for a same-origin PWA it adds a bootstrap dance, a custom `/auth/refresh` endpoint, and client-side token-management state without meaningfully improving the security posture over a single HttpOnly cookie.

**Implementation.** Nothing to build. fastapi-users' `CookieTransport` issues the session JWT on login and clears it on logout; there is no refresh path to implement.

**Future work.** If the project ever exposes a programmatic API for non-browser clients (e.g., researchers querying simulation results via curl, or a future native mobile client), a separate bearer-token authentication backend can be added alongside the cookie backend — fastapi-users supports multiple backends on the same `FastAPIUsers` instance. That is orthogonal to the PWA session story and is explicitly out of Slice 1 scope. Within the PWA session story, the relevant future work is DB-backed session revocation (a `sessions` table with per-session revoke, instead of a stateless JWT) — the same hardening that RFC 9700 §4.14 recommends for refresh tokens applies equally to a long-lived session JWT.

**Rejected alternatives.**

- *Dual-token (in-memory access + refresh cookie).* Discussed above.
- *Stateless refresh with rotation.* A previous draft of this document specified this (fastapi-users default `JWTStrategy` on the refresh cookie, custom `/auth/refresh` endpoint). Rejected in favour of the simpler single-cookie design described in §5 — the security properties are equivalent for our threat model and the PWA UX is strictly better.
- *DB-tracked refresh with family revocation (RFC 9700).* The gold standard for public OAuth clients; rejected on scope grounds — the implementation effort (schema + reuse detection + audit hooks + tests for replay) is disproportionate to thesis scope, and the upgrade path to a session-table variant is straightforward when needed.

**References.**

- RFC 6749 — OAuth 2.0, §10.4 (Refresh Token Security) — not applicable when no refresh token is issued
- RFC 9700 — OAuth 2.0 Security Best Current Practice, §4.14 (refresh-token rotation and reuse detection) — same
- Auth0, *Silent Authentication* — contrasting mobile-vs-SPA token strategies

---

## 7. Rate limiting: deferred to the reverse proxy (Nginx)

**Decision.** Rate limiting is applied at the reverse proxy layer (Nginx `limit_req` module) in production, not in application code. Development and tests run without rate limiting.

**Rationale.**

- *Composition with fastapi-users.* Application-level rate limiting via `slowapi` would require either wrapping fastapi-users' pre-built `get_register_router` / `get_auth_router` with custom endpoints (negating the "use the library natively" principle for Slice 1) or pattern-matching middleware against path strings (fragile — paths can drift, and path matching in ASGI middleware is awkward).
- *Nginx is in the critical path anyway.* The Hetzner deployment (PLAN.md phase 6) terminates TLS and reverse-proxies to the Uvicorn worker via Nginx regardless. `limit_req` is one configuration block in the same Nginx config that already handles TLS and static serving — it costs nothing incremental to add.
- *Operationally mature.* Nginx `limit_req` uses a leaky-bucket algorithm with a shared-memory zone keyed on `$binary_remote_addr`; it is widely deployed and well-understood. No Python dependency, no middleware to reason about, no per-request overhead inside the app.
- *Dev/test scope.* Local development and CI tests have no automated attackers to rate-limit against; adding limits there would complicate the test story (timing-dependent 429s) for no benefit.

**Implementation.** Phase 6 (deployment), not Slice 1. Nginx configuration:

```nginx
limit_req_zone $binary_remote_addr zone=auth_login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=auth_register:10m rate=10r/m;

location /auth/login    { limit_req zone=auth_login    burst=0 nodelay; proxy_pass http://backend; }
location /auth/register { limit_req zone=auth_register burst=0 nodelay; proxy_pass http://backend; }
```

A 429 response is emitted by Nginx directly when the limit is exceeded.

**Limitations acknowledged.**

- Per-IP limits are bypassable by botnets and IPv6 address rotation (same caveat as any IP-based scheme).
- Behind a CDN, `$remote_addr` is the CDN's IP; `$http_x_forwarded_for` must be used with `set_real_ip_from` configured for the CDN's ranges, or the entire site is vulnerable to IP-spoofed `X-Forwarded-For` headers. We are not behind a CDN; the direct-to-Nginx Hetzner setup avoids this class of bug.
- In a fully production-grade design this would be combined with per-account lockout (see §8) — that combination remains deferred.

**Rejected alternatives.**

- *`slowapi` in application code.* Does not compose cleanly with fastapi-users' pre-built routers without writing custom login / register endpoints, which was the point we were trying to avoid.
- *`fastapi-limiter`.* Would compose via `Depends(...)` on `include_router`, but requires Redis — a new service to operate and a new failure mode. Not justified at single-VPS scale.
- *Per-endpoint middleware with path matching.* Fragile against path changes; no advantage over the reverse-proxy layer.

**References.**

- Nginx documentation — `ngx_http_limit_req_module`
- OWASP Authentication Cheat Sheet §"Common Authentication Errors"
- OWASP ASVS v4.0.3 §V2.2.1 (anti-automation)
- NIST SP 800-63B §5.2.2 (rate-limiting authentication attempts)

---

## 8. Per-account lockout — deferred

**Decision.** Not implemented in Slice 1. Per-IP rate limiting (§7) is the sole brute-force defence in scope.

**Rationale.** Per-account lockout — locking an account for N minutes after K failed logins — is the canonical complement to per-IP rate limiting and is recommended by OWASP and NIST. It is cheap to add (`failed_login_attempts` and `locked_until` columns on `users`, plus a few lines in the auth pipeline). It is omitted from Slice 1 because (a) per-IP rate limiting alone is sufficient against opportunistic attackers at our user scale, and (b) the implementation requires hooking into fastapi-users' authentication path in a way that is fragile across library upgrades. The trade is documented honestly: for a real production deployment serving general internet traffic this would be required.

**Future work.** Add `failed_login_attempts: int default 0` and `locked_until: datetime | None` to the user model. After 5 consecutive failures lock for 15 minutes (return `423 Locked`, RFC 4918). Reset on successful login.

**References.**

- OWASP ASVS v4.0.3 §V2.2.1 (anti-automation), §V2.2.5 (account lockout policy)
- NIST SP 800-63B §5.2.2 (rate-limiting authentication attempts)
- RFC 4918 §11.3 (HTTP 423 Locked)

---

## 9. Generic 401 with constant-time auth path

**Decision.** All authentication failures return a single generic `401 "Invalid credentials"`, regardless of whether the email exists. When the email does not exist, the password verifier still performs work comparable in latency to the existing-user case.

**Rationale.** Differential responses ("Invalid email" vs "Invalid password") are a confirmed user-enumeration oracle. Differential *latency* is the same oracle by another mechanism: if existing-user logins take ~50 ms (the Argon2id cost) and missing-user logins return in <5 ms, an attacker can enumerate the user database by timing alone. Equalising both the response and the latency closes both oracles. This pattern is recommended by OWASP and is a routine finding in penetration tests of SPA-style applications.

**Implementation.** Slice 1. fastapi-users returns a generic 400/401 on bad credentials by default and runs the password hasher even when the user lookup misses (its `PasswordHelper.verify_and_update` is invoked with a dummy hash for the absent-user case). The timing-equivalence property is a documented library behaviour; we rely on it rather than adding an empirical timing-equivalence test, which would be inherently flaky on CI due to container scheduling noise and CPU frequency variability.

**Trade-off acknowledged.** Slightly worse UX — users cannot tell whether they mistyped their email or their password. Account-recovery flows (out of Slice 1 scope) provide the safe path to recovery without introducing the oracle.

**References.**

- OWASP Authentication Cheat Sheet §"Authentication and Error Messages" and §"Authentication Responses"
- CWE-204 — Observable Response Discrepancy
- CWE-208 — Observable Timing Discrepancy

---

## 10. Lightweight audit logging of authentication events

**Decision.** Auth-relevant events are logged through the standard library `logging` module with a JSON formatter: `register`, `login_ok`, `login_fail`, `refresh_ok`, `logout`. Each line includes timestamp, event type, user_id (when known), IP, and User-Agent. Logs go to stdout, captured by Docker.

**Rationale.** Auditability of authentication is required by every mainstream security framework (PCI-DSS §10.2, SOC 2 CC7.2, ISO 27001 A.12.4). None formally apply to a thesis project, but demonstrating awareness is academically defensible. Stdlib `logging` with structured (JSON) output is sufficient at our scale; a persisted `auth_events` table with full immutability semantics is over-engineering for Phase 1 and is documented as future work.

**Implementation.** Slice 1. `app/utils/audit.py` exposes a single `audit(event, **fields)` helper backed by stdlib `logging` with `python-json-logger`. Hooks invoke it from the register/login/logout endpoints; `/auth/refresh` emits `refresh_ok`. No additional infrastructure.

**Future work.** Persist auth events into an immutable `auth_events` table (append-only, with `(user_id, timestamp)` index for per-user audit queries). Add `login_locked` and `refresh_reuse_detected` events once §6 and §8 are implemented.

**References.**

- OWASP ASVS v4.0.3 §V7 (Error Handling and Logging)
- OWASP Logging Cheat Sheet
- PCI-DSS v4.0 §10.2 (illustrative — not in scope for the thesis app)

---

## 11. Password policy: length-only, NIST-aligned

**Decision.** Minimum length 12 characters. No composition rules (no "must contain uppercase, digit, and symbol"). No upper bound (Argon2id has no practical input length limit, unlike bcrypt's 72-byte ceiling).

**Rationale.** NIST SP 800-63B (2017, retained in Rev 4 / 2024) explicitly recommends *against* composition rules and against periodic forced rotation, on the empirical grounds that both push users toward predictable patterns ("Password1!" → "Password2!"). Length is the dominant factor in passphrase strength; a 12-character passphrase has greater entropy than a typical 8-character "complex" password. The 12-character floor reflects the post-2020 practitioner consensus — many older sources still cite 8, but 8 is now considered too short given commodity GPU cracking rates. Adopting Argon2id (§3) removes the 72-byte ceiling that bcrypt would have imposed.

**Implementation.** Slice 1. fastapi-users exposes a `validate_password` hook on the user manager; the implementation enforces length ≥ 12 and raises `InvalidPasswordException` with a clear message otherwise. Frontend mirrors the rule for inline validation but never trusts client-side checks.

**Future work.** Integrate the Have I Been Pwned (Pwned Passwords) k-anonymity range API on registration and password change to reject passwords known to have appeared in breach corpora. Single network call per password set; pseudonymous (only the first 5 SHA-1 hex chars are sent).

**References.**

- NIST SP 800-63B §5.1.1 (Memorized Secrets)
- OWASP Authentication Cheat Sheet §"Password Strength"
- Hunt, *Have I Been Pwned* — Pwned Passwords API documentation

---

## 12. OAuth identities in a separate `oauth_account` table

**Decision.** OAuth provider links (Google now, possibly Apple/GitHub later) live in a separate `oauth_account` table joined to `users` by `user_id`, with a unique constraint on `(oauth_name, account_id)`. We do *not* add `google_sub` (or per-provider columns) to `users`.

**Rationale.**

- *Many-to-one cardinality.* A single user may eventually link multiple providers; per-provider columns do not scale beyond the first.
- *Schema clarity.* `(provider, provider_user_id) → user` is a natural many-to-one join expressed by a join table; a sparse-column model with mostly-null per-provider columns is a schema smell.
- *Constraint enforcement.* The unique constraint on `(provider, provider_user_id)` makes "two users with the same Google account" structurally impossible, rather than depending on application code to check.

**Implementation.** Slice 2. fastapi-users provides a built-in `oauth_account` table via the `SQLAlchemyBaseOAuthAccountTableUUID` mixin with exactly this schema: `(id, user_id, oauth_name, access_token, refresh_token, expires_at, account_id, account_email)` and the required unique constraint. No custom table needed. Google flow (OAuth 2.0 + PKCE + ID-token verification) is provided by `httpx-oauth`, exposed via fastapi-users' `get_oauth_router`.

**Rejected alternatives.** A `google_sub` column on `users` (simplest for one provider; immediate refactor pain when adding the second); a JSON column listing identities (flexible but loses unique-constraint enforcement).

**References.**

- fastapi-users documentation, *OAuth2*
- httpx-oauth documentation, *Google*
- Standard pattern in production identity systems (Auth0, Clerk, Supabase, Keycloak)
- Fowler, *Patterns of Enterprise Application Architecture* (2002) — Foreign Key Mapping

---

## Summary: Slice 1 vs future work

| # | Decision | Slice 1 | Future work |
|---|---|---|---|
| 1 | UUID v4 PK | ✓ | — |
| 2 | `citext` email | ✓ | — |
| 3 | Argon2id hashing | ✓ | — |
| 4 | JWT HS256 + audience claim | ✓ | — |
| 5 | Single JWT in HttpOnly cookie | ✓ | — |
| 6 | No refresh tokens (PWA-specific rationale) | ✓ (N/A) | DB-backed session revocation if server-side logout becomes a hard requirement |
| 7 | Rate limiting at Nginx (not in app) | deferred to phase 6 (infra) | Application-level limits if ever needed beyond the reverse proxy |
| 8 | Per-account lockout | — | `failed_login_attempts` + `locked_until` |
| 9 | Generic 401 + constant-time | ✓ (library default) | — |
| 10 | Audit logging | partial (stdlib JSON logs) | persisted `auth_events` table |
| 11 | Length-only password policy | ✓ | HIBP k-anonymity check on set |
| 12 | `oauth_account` join table | ✓ (Slice 2) | — |

The deferred items are documented as future work in the thesis rather than absent — academic honesty about scope is a strength, not a weakness.
