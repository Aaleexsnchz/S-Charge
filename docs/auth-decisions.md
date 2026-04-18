# Authentication Architecture — Decision Record

Background notes for the Phase 1 authentication slice (see [phase-1.md](phase-1.md)). Each entry records a decision, its rationale, how it is realised in the implementation, the alternatives considered and rejected, and primary references suitable for footnoting in the thesis.

## Implementation substrate

Slice 1 is built on top of [fastapi-users](https://fastapi-users.github.io) with PostgreSQL + SQLAlchemy. The library handles the user model scaffolding, register/login/me endpoints, password hashing pipeline, JWT issuance, and (in Slice 2) the OAuth2 social-login flow via [httpx-oauth](https://github.com/frankie567/httpx-oauth). Custom code is added only where the library's defaults don't match the decisions below — chiefly for the refresh-cookie strategy, rate limiting, audit logging, and `citext` email storage. Reinventing the auth pipeline from primitives was considered and rejected as scope inappropriate for a thesis whose contribution lies elsewhere (data integration + simulation + algorithm work).

These decisions are locked for Slice 1. Subsequent changes should be appended as new entries (with date and reason) rather than edited in place.

---

## 1. UUID v4 as primary key for `users`

**Decision.** User IDs are random UUIDs (`gen_random_uuid()` from PostgreSQL's `pgcrypto`), not auto-increment integers.

**Rationale.** The user PK is exposed in URLs, JWT `sub` claims, and (later) in shared resources like booking and private-point ownership. Sequential integers leak (a) total user count and growth rate, (b) registration order, and (c) make it trivial to enumerate or guess neighbouring resources by incrementing the ID. UUID v4 has 122 bits of entropy — non-guessable in practice.

**Implementation.** Slice 1. fastapi-users supports UUID primary keys natively via its `SQLAlchemyBaseUserTableUUID` base class.

**Rejected alternatives.** `BIGSERIAL` (smallest, fastest index, but enables enumeration); UUID v7 (time-ordered, better B-tree locality, but PostgreSQL native support landed only in v18 and Python ecosystem support is uneven); Snowflake/KSUID (require an external generator).

**Trade-offs accepted.** 16-byte vs 8-byte index entries and minor B-tree fragmentation due to random insert order. Negligible at thesis-app scale.

**References.**

- RFC 9562 — Universally Unique IDentifiers (UUIDs), §5.4 (v4)
- OWASP ASVS v4.0.3 §V8.3.1 (non-sequential identifiers for sensitive resources)
- PostgreSQL documentation — pgcrypto, `gen_random_uuid()`

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
- *No `passlib`.* `passlib` 1.7.4 is unmaintained (last release 2020) and emits incompatibility warnings against modern hashing-library versions. `argon2-cffi` is used directly.
- *Auto-rehash on verify.* `PasswordHasher.check_needs_rehash()` lets us upgrade existing hashes silently when parameters tighten in future, with no migration needed.

**Implementation.** Slice 1. fastapi-users supports custom password hashers via its `PasswordHelperProtocol`; an `Argon2PasswordHelper` thin wrapper around `argon2-cffi` is registered.

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

## 5. Token transport: in-memory access token + httpOnly refresh cookie

**Decision.** The access token is returned in the JSON response body and held only in JavaScript memory on the client (React state). The refresh token is delivered as an `HttpOnly; Secure; SameSite=Lax` cookie scoped to the `/auth/refresh` path.

**Rationale.**

- *XSS exposure of `localStorage`.* Any token placed in `localStorage` or `sessionStorage` is reachable by any JavaScript executing in the page. Realistic XSS vectors include `dangerouslySetInnerHTML`, third-party scripts (analytics, A/B testing, embedded chat widgets), and supply-chain compromise of any npm dependency — and for a project that depends on MUI, Leaflet, and Recharts, the transitive dep tree is wide. Token theft from `localStorage` is the dominant SPA credential-loss pattern in industry post-mortems.
- *`HttpOnly` cookie.* Cannot be read by JavaScript at all; the refresh token cannot be exfiltrated by XSS. XSS can still issue authenticated requests as the victim, but only from within the victim's browser session — it cannot persist the credential elsewhere or use it offline.
- *`SameSite=Lax`.* Blocks the cookie from cross-site sub-requests, neutralising most CSRF vectors. Because frontend and backend are reverse-proxied through a single Nginx on the same origin in production, `Lax` is sufficient; `Strict` would interfere with the OAuth callback redirect.
- *`Secure`.* Cookie only transmitted over TLS in production (overridden in local dev).
- *Path scope `/auth/refresh`.* The cookie is attached only to refresh requests, never to ordinary API calls — minimising accidental exposure surface.

**Implementation.** Slice 1. fastapi-users provides a `CookieTransport` that we configure for the refresh token (`HttpOnly`, `Secure`, `SameSite=Lax`, path `/auth/refresh`) and a `BearerTransport` for the access token. A small custom `/auth/refresh` endpoint reads the cookie, validates the refresh JWT, and issues a fresh access token (and rotates the refresh cookie).

**Rejected alternatives.** Both tokens in `localStorage` (maximum XSS exposure); access token in cookie + double-submit CSRF token (viable but adds CSRF infrastructure across every API call instead of confining the cookie surface to one endpoint).

**References.**

- OWASP ASVS v4.0.3 §V3.4 (Cookie-Based Session Management)
- OWASP Cross-Site Scripting Prevention Cheat Sheet
- OWASP Session Management Cheat Sheet
- MDN Web Docs — *Set-Cookie* (`HttpOnly`, `SameSite`, `Secure` attributes)
- Degges (Auth0, 2018), *Please Stop Using Local Storage* — widely cited industry source on the SPA token-storage debate

---

## 6. Refresh tokens: stateless JWT with rotation; family revocation deferred

**Decision.** Refresh tokens are stateless JWTs (no DB row per token). On each `/auth/refresh` call a new refresh token is minted and the cookie is overwritten — the old token is no longer presented by the legitimate client, but is *cryptographically* still valid until its `exp` (14 days). Logout clears the cookie client-side.

**Rationale.** A fully stateful design — DB-tracked tokens with `replaced_by` chains and reuse-detection that revokes the entire token family — is the gold standard for SPA auth and is recommended by RFC 9700 for public clients. It was specified in an earlier draft and rejected on scope grounds: the substantive thesis contribution lies in Phases 3–4 (data integration, simulation, algorithm) and the implementation effort for stateful refresh (DB schema + reuse detection + audit hooks + tests for replay) is best invested there. The stateless design is the standard fastapi-users default and is sufficient against opportunistic threats; it is materially weaker against a determined attacker who has already obtained a refresh token (no session can be revoked server-side; logout is best-effort).

**Implementation.** Slice 1. fastapi-users default `JWTStrategy` for the refresh token, with cookie transport. `/auth/refresh` is a thin wrapper that invokes the library's token-refresh path.

**Future work.** Replace stateless refresh with a DB-backed `refresh_tokens` table (`id` = jti, `user_id`, `issued_at`, `expires_at`, `revoked_at`, `replaced_by`, `user_agent`, `ip`). Each refresh rotates: old row marked revoked, new row chained via `replaced_by`. Presenting a token whose `revoked_at IS NOT NULL` triggers revocation of the entire chain (`refresh_reuse_detected` audit event). This is the model in RFC 9700 §4.14.2.

**Rejected alternatives (still rejected).** Single long-lived refresh token without rotation (no defence against replay).

**References.**

- RFC 6749 — OAuth 2.0, §10.4 (Refresh Token Security)
- RFC 9700 — OAuth 2.0 Security Best Current Practice, §4.14 (refresh-token rotation and reuse detection)
- Auth0 documentation, *Refresh Token Rotation*

---

## 7. Per-IP rate limiting

**Decision.** `slowapi` middleware with an in-memory backend. Limits: `/auth/login` 5 req/min/IP, `/auth/register` 10 req/hour/IP, `/auth/refresh` 30 req/min/IP. Migration path to Redis backend if multi-process deployment becomes necessary.

**Rationale.** Rate limiting is the first-line defence against credential stuffing and brute-force. Limits are loose enough that no real user will hit them under normal conditions, tight enough to make automated attacks economically expensive. In-memory state is appropriate for a single-VPS, single-Uvicorn-process deployment; a Redis backend would be over-engineering at this scale.

**Implementation.** Slice 1. A `slowapi.Limiter` is registered as application middleware in `app/main.py`; decorators are applied to the fastapi-users register/login endpoints (which we expose via the library's pre-built routers) and to our custom `/auth/refresh` endpoint.

**Limitations acknowledged.** Per-IP limits are bypassable by botnets and IPv6 address rotation. In a fully production-grade design this would be combined with per-account lockout (see §8) — that combination is deferred. Nginx's `limit_req` could be added as defence-in-depth at the reverse proxy layer.

**References.**

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

**Implementation.** Slice 1. fastapi-users returns a generic 400/401 on bad credentials by default and runs the password hasher even when the user lookup misses (its `PasswordHelper.verify_and_update` is invoked with a dummy hash for the absent-user case). No custom code required beyond confirming the behaviour with a timing-equivalence test.

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
| 5 | In-memory access + HttpOnly refresh cookie | ✓ | — |
| 6 | Refresh-token rotation | partial (stateless rotation) | DB-tracked rotation + family revocation on reuse |
| 7 | Per-IP rate limiting | ✓ | — |
| 8 | Per-account lockout | — | `failed_login_attempts` + `locked_until` |
| 9 | Generic 401 + constant-time | ✓ (library default) | — |
| 10 | Audit logging | partial (stdlib JSON logs) | persisted `auth_events` table |
| 11 | Length-only password policy | ✓ | HIBP k-anonymity check on set |
| 12 | `oauth_account` join table | ✓ (Slice 2) | — |

The deferred items are documented as future work in the thesis rather than absent — academic honesty about scope is a strength, not a weakness.
