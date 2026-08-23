---
id: auth-0002
status: accepted
phase: 1
date: 2026-03
related: [auth-0001]
---

# auth-0002: Single HttpOnly cookie session — no refresh tokens


**Decision.** Authentication state is a single JWT in an `HttpOnly; Secure; SameSite=Lax` cookie at path `/`, 14-day lifetime. No access/refresh pair, no bearer tokens, no `/auth/refresh` endpoint.

## Rationale — cookie transport

- *`HttpOnly`* makes the token unreadable by JavaScript, neutralising the dominant SPA credential-loss vector: XSS exfiltration from `localStorage` / `sessionStorage`. XSS can still issue authenticated requests while the page is open, but cannot persist or exfiltrate the credential.
- *`SameSite=Lax`* blocks the cookie from cross-site sub-requests, addressing CSRF for a same-origin app served with the API behind one reverse proxy. `Strict` would break the OAuth callback redirect (Slice 2).
- *`Secure`* enforces TLS in production (relaxed in local dev).
- A PWA is a same-origin web app; cookies are sent automatically by the browser, including on service-worker fetches and after a cold start — no client-side token management.

## Rationale — no refresh tokens

The dual-token pattern (in-memory access + cookie refresh + periodic `/auth/refresh`) originates in mobile apps and multi-origin OAuth, where bearer tokens are presented to third-party APIs and access tokens can't sit in a cookie. For a same-origin PWA the problems it solves are mostly not ours:

- *No third-party API.* The PWA talks only to our backend; bearer tokens aren't required.
- *"Short access TTL limits blast radius if stolen"* is defeated for SPAs anyway: XSS owns the page regardless of where the token lives, and `HttpOnly` on a single long-lived cookie prevents exfiltration just as effectively as splitting the credential.
- *"Refresh rotation enables revocation"* is not in our threat model — the stateless refresh design can't revoke an in-flight refresh token before its `exp` either.
- *Cold-start cost.* A memory-only access token is lost when the user closes the PWA window. Every launch then pays for a bootstrap `/auth/refresh` round-trip before any real call.
- *Service-worker background sync* can't read a memory-only access token without stashing it in `IndexedDB` / `localStorage`, which negates the XSS protection that was the point. Cookies are sent automatically.

## Implementation

Slice 1. fastapi-users' `CookieTransport` configured with our security flags, composed with a single `JWTStrategy` (HS256, 14-day lifetime, audience `s-charge:session`) into one `AuthenticationBackend`. Logout is `CookieTransport.get_logout_response()` (library-provided), which clears the cookie with `Max-Age=0`. No custom endpoints.

## Consequences

- **Sessions cannot be revoked.** The JWT is stateless, so a stolen cookie stays valid until it expires — up to 14 days. Nothing in the app can log another device out. Accepted for a thesis demo; the upgrade path is a session table, which is the same work as DB-backed refresh rotation.
- XSS can act as the user while the page is open, but cannot exfiltrate the credential. That is the ceiling this design buys, and it is the honest answer to "is this resistant to session theft?" — see [thesis/robo-de-sesion.md](../thesis/robo-de-sesion.md).
- `SameSite=Lax` rather than `Strict` is a requirement of the OAuth callback redirect, not a preference.
- Everything must stay same-origin. A split frontend/API origin would force `SameSite=None` and reintroduce the CSRF surface this avoids — which is why [infra-0001](infra-0001-deployment.md) puts both behind one reverse proxy.

## Rejected alternatives

- *`localStorage` storage.* Maximum XSS exposure — forbidden.
- *Dual-token (in-memory access + HttpOnly refresh cookie).* Industry-standard SPA pattern; rejected for the PWA-specific reasons above. An earlier draft specified it before the trade-offs were re-examined.
- *DB-tracked refresh with family revocation (RFC 9700).* Gold standard for public OAuth clients; out of thesis scope. Upgrade path to a session-table variant is straightforward when needed.
- *Access token in cookie + double-submit CSRF token.* Viable but adds CSRF infrastructure across every API call — unnecessary when `SameSite=Lax` already addresses the threat.

## References

- OWASP ASVS v4.0.3 §V3.4 (Cookie-Based Session Management)
- OWASP Cross-Site Scripting Prevention Cheat Sheet
- MDN — *Set-Cookie* (`HttpOnly`, `SameSite`, `Secure`)
- RFC 9700 — OAuth 2.0 Security Best Current Practice §4.14
