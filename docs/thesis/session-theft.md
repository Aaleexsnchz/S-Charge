---
title: Session theft and bearer-token replay
status: draft (thesis writeup, concept-level)
---

# Session theft and bearer-token replay

The session mechanics in [auth.md](auth.md) defend against the standard SPA threat model: XSS exfiltration, CSRF, credential stuffing, and unverified-account abuse. They do **not** defend against the route to account takeover that has dominated consumer-account incident reports since 2024 — **session cookie theft by information-stealer malware running on the user's own machine, followed by replay from an attacker-controlled browser**. This chapter records why that gap exists, why it cannot be closed inside an application, and where the defensive frontier sits.

## The threat

A compromised endpoint — typically the result of a social-engineering vector such as a fake CAPTCHA prompting the user to paste a script into a terminal ("ClickFix") — runs an information stealer (Lumma, Vidar, StealC, historical RedLine) under the user's own OS account. The stealer reads the browser's cookie store, saved passwords, `localStorage`, and browser fingerprint, and uploads them as a "log" sold on commodity markets. The buyer loads the log into an **anti-detect browser** (Octo, Genesium, Dolphin{anty}) configured with a **residential proxy** geolocated near the victim, presents the stolen session cookie, and is authenticated as the victim from the first request.

Two properties make the attack hard to detect at the relying-party layer:

- *The stolen cookie is a complete proof of identity.* It is the *output* of a previously successful login, with any MFA factors already satisfied. No re-authentication step is invoked; MFA is not re-prompted.
- *The attacker presents the victim's fingerprint and approximate IP geography.* `User-Agent`, canvas hash, WebGL hash, timezone, and language all match. The identity provider's risk engine, which relies on anomaly signals, sees no anomaly. "Recent activity" dashboards continue to attribute requests to the device that *minted* the session, not the host making each individual request.

A user with hardware MFA enrolled, no password reuse, and no new-device sign-ins on record can still lose every account whose session cookies were present in the browser profile at the moment the stealer ran.

## The bearer-token problem

The root cause is architectural rather than implementational: HTTP session cookies are **bearer tokens**. Possession of the token string is, by protocol, equivalent to possession of the credential. Nothing in the request chain ties the token to the device that issued it. Every modern web session — `HttpOnly` cookies included — has this property once the cookie reaches an attacker.

The session design in [auth-0002](../decisions/auth-0002-cookie-session.md) is explicit about scope: `HttpOnly` neutralises **JavaScript** exfiltration (XSS), and that is its design goal. It cannot neutralise exfiltration by **native code running as the same OS user as the browser**, because no application can. On a single-user desktop OS, the security boundary is the process the user chooses to run, not the application that holds the credential — the browser's cookie store is, of necessity, readable by the browser process, which runs as the user, alongside any other code the user runs.

## What an application can do

Defences against bearer-token replay fall into three categories:

| Category | Mechanism | Effect |
|---|---|---|
| Make the token non-bearer | [DBSC][dbsc] (Device-Bound Session Credentials), [DPoP][dpop] (RFC 9449) | Each request carries a signature from a key resident in the device's TPM / Secure Enclave. The cookie alone is insufficient; the signing key cannot be exfiltrated by user-space code. Addresses the root cause. |
| Re-authenticate before sensitive actions | WebAuthn / passkey step-up on email change, password change, OAuth consent to new relying parties | The stolen session can browse but cannot escalate. Closes the takeover pivot characteristic of real incidents (stolen session → "Sign in with Google" at a third party → password-reset link to inbox read with the same session → permanent takeover). |
| Limit the blast radius if a token is stolen | Short TTLs, refresh rotation with reuse detection, DB-backed server-side revocation | Reduces the window of exploitation; does not prevent it. |

The first two categories are the consequential ones. DBSC in particular, rolling out through Chrome and Google during 2025–26, is the first widely-deployed mechanism that breaks the bearer-token assumption for everyday web sessions — and because it applies at the identity-provider layer, every OAuth-derived session downstream of a DBSC-protected Google account inherits some of the benefit.

## What this project does, and what it does not

The TFM session implements category three only: an `HttpOnly; Secure; SameSite=Lax` JWT cookie with a 14-day TTL ([auth-0002](../decisions/auth-0002-cookie-session.md)), with DB-backed revocation as plausible future hardening. Category one is not implemented: DBSC is browser-vendor-led and not yet a stable relying-party-facing primitive, and DPoP would require a non-cookie transport that auth-0002 specifically rejects for a same-origin PWA. Category two — WebAuthn step-up on sensitive actions — is feasible at the application layer and a credible Phase-3-onward addition, but is out of Phase 1 scope: the account-modifying surface in Phase 1 is small (password change, email change, both gated by email-link verification at the IdP) and does not justify the WebAuthn ceremony cost on its own.

The honest viva answer to *"why isn't this resistant to session theft?"* is that no current application is, under the bearer-token model. The two defences that change this answer are either not yet a relying-party-exposed primitive (DBSC) or an incrementally addable hardening rather than a Phase 1 omission (WebAuthn step-up). The cookie session in [auth-0002](../decisions/auth-0002-cookie-session.md) is sized to the dominant SPA threats; the post-endpoint-compromise threat is recognised as out of scope rather than overlooked.

## Reference incidents

The pattern reached public visibility through infostealer-driven takeovers of high-profile accounts on platforms with no step-up requirement for sensitive actions — most prominently consumer chat and gaming services during 2024–25. The mechanics are consistent: stealer → cookie log → anti-detect browser → "Sign in with Google" or equivalent → email-based reset link → permanent takeover. The same pattern is the motivating example for the DBSC working group's draft and for Google Advanced Protection's expansion of FIDO2 re-prompts to OAuth consent flows during 2025.

[dbsc]: https://w3c.github.io/webappsec-dbsc/
[dpop]: https://datatracker.ietf.org/doc/html/rfc9449
