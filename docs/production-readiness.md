# Production readiness

**What this application would need to serve real users, and does not have.**

This is a master's thesis prototype deployed for one demo instance. Its architecture is deliberately sized for that: a single VPS, a compose stack, nightly dumps, and no on-call. Those are correct choices at this scale — the point of this file is to show they are *choices*, by naming precisely what each one would have to become if the system carried real users, real money and real uptime obligations.

**This is not [ideas-backlog.md](ideas-backlog.md).** That file parks optional features nobody has committed to building. This one is a register of **known gaps against production-grade operation** — every entry is something a real deployment requires and this one knowingly omits. Nothing here is a feature idea, and nothing here is scheduled unless a phase is named.

Read it as the answer to *"why didn't you do X?"* — the honest answer is usually "because at one user on one box it costs more than it returns", and that reasoning is recorded per item so a reader can distinguish engineering judgement from oversight.

Where an item is already argued in depth elsewhere, this file links out rather than repeating it. The scaling architecture itself — where one box breaks first and what replaces each part — is a thesis chapter, outlined in [plan.md](plan.md) Phase 14 and to be written as `thesis/despliegue-y-escalado.md`.

---

## Availability and deployment

**Single point of failure.** One VPS means every deploy, reboot and kernel update is an outage, and a host failure is a total outage of unbounded length. Production wants at least two app nodes behind a load balancer, which in turn requires the app to be stateless (it is — sessions are JWTs, see below) and the database to move off the box.

**Images are built on the production host.** `docker compose up -d --build` is why the host spec has a 4 GB floor: a Vite production build competes with Postgres for RAM. It also means the artifact running in production was never the artifact CI tested — it was rebuilt from the same source, which is not the same guarantee. Production builds once in CI, pushes to a registry, and has the server pull an immutable digest. That also turns rollback into a pull instead of a rebuild.

**No staging environment.** Production is the only place the production configuration has ever run. Migrations meet production-shaped data for the first time in production.

**Deploys are not zero-downtime, and migrations are not backwards-compatible.** The current deploy replaces containers and then migrates, leaving a brief window where new code runs against the old schema ([phases/phase-5.md](phases/phase-5.md) Slice 5). With rolling deploys across multiple nodes this stops being a window and becomes a guarantee: both versions run simultaneously, so every migration must follow **expand/contract** — add nullable, write both, backfill, drop in a later release. This is the single largest discipline change on the path to multi-node, and it constrains how every future migration is written.

## Data and durability

**Backups are nightly logical dumps.** `pg_dump` to Backblaze B2 ([operations.md](operations.md)) gives an RPO of up to 24 hours — a bad afternoon loses a day. Production wants continuous WAL archiving and point-in-time recovery, so the recovery target is minutes.

**Restores are verified by hand, if at all.** A backup nobody has restored is a hypothesis, not a backup. Production verifies restores automatically and on a schedule. *Scheduled: [plan.md](plan.md) Phase 13.*

**Postgres is self-managed.** Failover, minor-version patching, and connection pooling are all manual or absent. A managed instance moves those to the provider; at scale you would also want a read replica, since the catalogue queries (~13.7k charging points) are read-dominated.

**No connection pooling.** The asyncpg pool is per-process. Multiple app replicas multiply connections against a fixed Postgres limit; production puts PgBouncer in front.

## Secrets and credentials

**Secrets are `.env` files on disk.** Anything that compromises the host reads `SECRET_KEY` — which signs every session JWT and therefore forges any user, including one with owner privileges. Production uses a secrets manager with short-lived credentials and automated rotation, so a host compromise does not hand over a permanent master key.

**No rotation procedure.** Secrets are rotated once, at first deploy ([setup/deployment.md](setup/deployment.md)). There is no routine, no schedule, and no way to rotate `SECRET_KEY` without invalidating every live session — because sessions are stateless and unrevocable.

**Production configuration exists in exactly one place, with no history.** The `.env` is uncommitted and lives only on the VPS, so losing the host loses the configuration, and nothing records what changed or when. The proportionate step is not a secrets manager but **SOPS + age**: the file committed encrypted and decrypted at deploy, which buys versioned, reviewable history against one key to protect. It does not remove plaintext at runtime — the values still reach the container environment — so it addresses recoverability and audit, not confidentiality against a compromised host. Why GitHub Secrets and Vault were both rejected for this: [decisions/infra-0001](decisions/infra-0001-deployment.md).

## Observability

**There is none.** The answer to *is it up, is it slow, did that error reach a user* is `docker compose logs`. This is the largest single gap in this list: at real scale you learn about incidents from users, and you cannot diagnose what you did not record.

Production needs error tracking (Sentry or equivalent), metrics and dashboards (Prometheus/Grafana), aggregated searchable logs, uptime checks from outside the host, and alerting that reaches a human.

The foundation is better than the absence suggests: the backend already emits structured JSON logs (`python-json-logger`) and already calls `audit()` on the security-relevant auth events. Those are the parts that are hard to retrofit. Shipping them somewhere is configuration.

**No SLOs, no runbooks, no incident process, no on-call.** Nobody is paged, because nobody is promised anything.

## Application security

**The Content-Security-Policy is incomplete.** Caddy ships the OWASP header set — HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `X-Frame-Options` — and a CSP carrying only `frame-ancestors 'none'`; `default-src`, `script-src`, `style-src`, `base-uri`, `form-action` and `object-src` are missing. `HttpOnly` prevents JavaScript from *reading* the session cookie, but an XSS payload can still issue authenticated requests with it — so CSP is the control that actually reduces the blast radius of the threat [thesis/robo-de-sesion.md](thesis/robo-de-sesion.md) analyses. The blocked directive is `style-src`: MUI and Emotion inject inline `<style>` tags, so a strict policy would force `style-src 'unsafe-inline'` and negate much of the benefit. Shipping the directives that do not depend on it, and recording why the remaining one is held back, is the honest interim. *Scheduled: [plan.md](plan.md) Phase 13.*

**Sessions cannot be revoked.** The session is a stateless JWT ([auth-0002](decisions/auth-0002-cookie-session.md)): a stolen token stays valid until it expires, and there is no logout-everywhere, no per-session audit, and no way to eject an attacker. Production backs sessions with a database table carrying `revoked_at`. Argued at length in [auth-0002](decisions/auth-0002-cookie-session.md) and [thesis/robo-de-sesion.md](thesis/robo-de-sesion.md); the same reasoning covers verification and password-reset tokens ([auth-0003](decisions/auth-0003-preregistration-shell-mitigation.md)).

**Rate limiting is in-process.** Once implemented ([phases/phase-5.md](phases/phase-5.md) Slice 13), the limiter's default storage is per-process memory. With N replicas that grants N times the intended limit, so the protection *weakens as you scale* — the opposite of the desired property. Production backs it with Redis.

**Nothing scans the built images or the code**, no SAST/DAST in CI, and no penetration testing. Renovate keeps dependencies current ([infra-0004](decisions/infra-0004-renovate-over-dependabot.md)) and GitHub's dependency alerts feed it, so a known-vulnerable package opens a PR out of schedule — but that covers the manifests, not the images built from them nor the code written here.

## Landmines specific to this codebase

Generic advice stops being useful here. These three would break in non-obvious ways, and they are properties of *this* system rather than of scale in general.

**The scheduler cannot be replicated.** `supercronic` runs inside a single container. Run two, and both fire `refresh_reve` on the same schedule against an API capped at **5 requests per hour** — the budget is exhausted instantly and the ETL enters a permanent rate-limited loop. Any move to multiple hosts requires a single explicitly-unreplicated scheduler, leader election, or a job queue with a distributed lock.

**Charging-point availability is not modelled** ([be-0002](decisions/be-0002-availability-not-modelled.md)). Points are shown as available with a disclaimer. A real product needs live status — a data-access problem, not an engineering one, and the schema already has the column waiting for a source.

Four routes exist today, none of them taken. The first two are **access rights**, not commercial negotiations, which is what makes this tractable:

1. **Ask for access to the official system.** The SGV already *receives* status and price: the Resolución de 2 de abril de 2025 obliges CPOs at 43 kW and above to send them over OCPI, and the public REVE map displays them. The data exists and is already centralised. Its interface answers `403 Missing Authentication Token` rather than `404`, which suggests a credentialed path exists — what is missing is knowing who grants it and on what terms. Cheapest route if it works.
2. **Invoke AFIR against each CPO.** Article 20.3 of Regulation (EU) 2023/1804 requires *every* CPO to expose an API giving "free and unrestricted access" to static **and dynamic** data, including operational status, availability and price. A CPO refusing is in breach of an EU regulation. The cost is fan-out — 142 operators — so this works better as the legal backing for route 1 than as the primary plan.
3. **Contract a roaming hub** (Hubject, Gireve). One agreement, hundreds of CPOs, over OCPI — which is already the schema. The industry's normal path, and the only one that also unlocks reservations via OCPI's `Commands` module (`RESERVE_NOW` / `CANCEL_RESERVATION`). Commercial and paid.
4. **Push for dynamic publication at the National Access Point.** This does not rest on interpreting AFIR: the Resolución de 2 de abril de 2025 states that the information sent to the SGV *"será publicada en el Punto de Acceso Nacional de Información de Tráfico"* — will be published, not may be. Spain currently serves only the static half: the DGT publishes `EnergyInfrastructureTablePublication` (verified 2026-08-06 — 85.5 MB, 12,337 sites, 36,972 refill points, 44,105 connectors, CC-BY, no API key) while the predictable `EnergyInfrastructureStatusPublication` paths return `404`. Slowest route, and the only one that would benefit any third party rather than just this application.

**The NAP is not a drop-in replacement for the seed source.** Measured on the full file: it carries **no price field at all**, so it cannot feed the price cascade that the cost simulation rests on. It would solve the licence question and the 5 req/hr cap, and nothing else. Reasoning in [thesis/memoria/05_Modelo_de_datos_y_fuentes.md](thesis/memoria/05_Modelo_de_datos_y_fuentes.md) and [10_Marco_regulador.md](thesis/memoria/10_Marco_regulador.md).

## Legal and compliance

**GDPR obligations are unaddressed.** The application stores personal data of EU subjects (`users`, `oauth_account`: email, name, provider identity). Real users make the following binding rather than optional: a published privacy policy, a lawful basis for processing, data-processing agreements with each processor (Hetzner, Resend, Google), a defined retention policy, a working right-to-erasure path, data-portability export, and breach notification within 72 hours.

None of this exists, and the erasure path is not merely a missing endpoint — deleting a user has to reckon with what happens to their sessions, bookings and ledger rows.

*Scheduled as thesis content: [plan.md](plan.md) Phase 14, alongside the business chapter.*

**The right to re-serve the mirrored catalogue is unestablished.** [be-0001](decisions/be-0001-reve-mirror-not-proxy.md) settled the engineering case for holding a local copy and never asked the legal one. The REVE API's terms of use could not be verified: the endpoint answers `403` without credentials and the legal notice is not retrievable by an automated client. Copying for one's own use and re-serving to the public are different acts, and a deployed instance does the second. Unresolved as of 2026-08-06 and **not to be asserted either way** — see [thesis/memoria/10_Marco_regulador.md](thesis/memoria/10_Marco_regulador.md).

**The position improved materially when the read endpoints were closed.** Every `/api/*` route except `/api/health` and the auth surface now requires a session, so the catalogue reaches authenticated users of this application rather than the public. Serving a mirrored dataset to one's own users is a far easier thing to defend than publishing it, and it narrows the question the thesis has to answer. It does not settle it.

There is a documented way out if this ever blocks anything: the DGT's National Access Point publishes the same catalogue under **CC-BY** with no key, so migrating the seed would turn an open question into an attribution line. It costs the price data (see above), so it is a trade, not a free fix.

**No terms of service, and no cookie/consent notice.** The session cookie is strictly necessary so it needs no consent banner under EU rules, but that conclusion should be documented rather than assumed.

## Process

**One developer, no review.** Every change is written and approved by the same person. Branch protection ([phases/phase-5.md](phases/phase-5.md) Slice 9) enforces that changes arrive through a pull request with green CI, which catches mechanical errors but not design ones.

**No load testing.** No measurement exists of where this stack saturates — concurrent connections, map-viewport query cost, or the RAM contention between a Vite build and Postgres during a deploy. The Phase 14 chapter argues where the box breaks first; nothing has measured it.

**Test coverage is not enforced.** Phase 13 targets ≥70% on `services/`; CI does not gate on coverage today.
