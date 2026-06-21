---
id: auth-0003
status: accepted
phase: Phase 1 / Slice 3
date: 2026-04
related: [auth-0001]
---

# auth-0003: Pre-registration shell attack mitigation

> Slice 3 decision. Merges the two halves of one threat-model fix; neither suffices alone.

## Threat model

Slice 2 mounts Google OAuth with `associate_by_email=True`. Without further mitigation this enables a **pre-registration shell attack**: an attacker registers a password account with the victim's email, then waits for the victim to sign in with Google; `associate_by_email` silently merges the two and the attacker now has a working password on the victim's account.

## Decision

Two complementary fixes, applied together.

1. **Verification gate.** Password registrations are unverified by default and gated from logging in (`requires_verification=True` on `get_auth_router`). Google OAuth users are auto-verified (`is_verified_by_default=True` on the OAuth router) since Google has already proven control of the address. Verification + password-reset emails go via [Resend](https://resend.com); tokens are fastapi-users' default 1-hour JWTs.
2. **OAuth-link hash reset.** `UserManager.oauth_callback` is overridden so that when a Google sign-in links to an existing email/password row whose `is_verified` is still false, it (a) flips `is_verified` to true and (b) replaces `hashed_password` with a fresh hash of a discarded random secret. The legitimate user can then `/forgot-password` to set a new password.

## Why both halves

- The verification gate alone breaks the legitimate "I had a password account, now I'm linking Google" flow — `associate_by_email=True` doesn't auto-verify the linked row, and `requires_verification=True` covers the entire auth router, blocking even logout.
- Naively flipping `is_verified=true` after the link would fix that but re-open the attack: the attacker's pre-set password would now satisfy both halves of the gate.
- Wiping the hash at the same moment the row is verified closes both holes in one transaction. This is the Auth0 / Clerk pattern ("merge a verified provider into an unverified credentials account, drop the credentials").

## Why Resend

SMTP at this stage means SPF/DKIM/DMARC for a domain we don't yet own (production domain lands in Phase 6). Resend's sandbox sender (`onboarding@resend.dev`) delivers without DNS setup, the free 100/day tier covers a thesis demo, and the Python SDK is a one-line swap when we cut over to a verified domain. Provider lock-in is minimal — the call sits in one helper module.

## Implementation

Slice 3.

- **Email helper** (`backend/app/services/email.py`): builds absolute URLs (`settings.app_base_url + "/verify-email?token=…"` and `…/reset-password?token=…`) and calls `resend.Emails.send`. Send failures are caught and emit an `email_send_failed` audit event rather than 500-ing the request.
- **User-manager hooks**: `on_after_register` calls `self.request_verify`; `on_after_request_verify` and `on_after_forgot_password` dispatch the relevant email; `on_after_verify` and `on_after_reset_password` emit audit events.
- **`oauth_callback` override**: calls `super().oauth_callback(...)`, then if the returned user is still unverified updates `is_verified=True` and overwrites `hashed_password` with `password_helper.hash(password_helper.generate())`. Emits an `oauth_link_reset_password` audit event.
- **Routers**: `get_verify_router` and `get_reset_password_router` mounted under `/auth`. Auth router uses `requires_verification=True`; Google OAuth router uses `is_verified_by_default=True`.
- **Frontend**: registration redirects to `/check-email`; `/verify-email?token=…` POSTs on mount; `/forgot-password` and `/reset-password?token=…` are full forms; login surfaces `LOGIN_USER_NOT_VERIFIED` as a "Reenviar correo" CTA.

The `if not user.is_verified` guard distinguishes the three `oauth_callback` branches without special-casing:

| Branch | Returned `user.is_verified` | Override fires? |
| --- | --- | --- |
| Returning user (matched by `oauth_account` row) | preserved (true) | no |
| New user with `is_verified_by_default=True` | true | no |
| `associate_by_email` matched an unverified password row | preserved (false) | yes |

## Token lifetime — 1h

fastapi-users' default. No revocation (stateless JWT). A server-side `verification_tokens` table with `revoked_at` is the same kind of work as DB-backed session revocation and is deferred for the same reasons. One-hour blast radius on a token that requires inbox access is acceptable.

## Rejected alternatives

- *Magic-link login (passwordless).* UX win but doesn't compose with the existing password path; would force a rewrite of OAuth-link semantics. Out of slice scope.
- *Server-side `verification_tokens` / `password_reset_tokens` tables with revocation.* Worth doing in production.
- *Flip `is_verified=true` without wiping the password.* Re-opens the attack.
- *Refuse to link an unverified row.* Rejects the legitimate Google sign-in entirely; the unique email constraint makes re-registration infeasible without first deleting the old row.
- *Drop `requires_verification=True` from logout only.* fastapi-users mounts login + logout under one router; splitting forks library code and misses the deeper issue (the linked account silently has an attacker-controlled password).

## References

- fastapi-users — *Verification*, *Password reset*, *Customising `oauth_callback`*
- Auth0, *Linking user accounts*
- OWASP ASVS v4.0.3 §V2.4, §V2.7, §V3.4
- Resend documentation
