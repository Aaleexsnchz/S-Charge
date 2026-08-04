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

**No Content-Security-Policy.** Caddy sets `Strict-Transport-Security` and nothing else. `HttpOnly` prevents JavaScript from *reading* the session cookie, but an XSS payload can still issue authenticated requests with it — so CSP is the control that actually reduces the blast radius of the threat [thesis/robo-de-sesion.md](thesis/robo-de-sesion.md) analyses. It is not implemented today because MUI and Emotion inject inline `<style>` tags, which would force `style-src 'unsafe-inline'` and negate much of the benefit; the Phase 6 migration to Tailwind compiles to a static stylesheet and makes a strict policy practical. *Scheduled: [plan.md](plan.md) Phase 13, after the Phase 6 migration.*

**Sessions cannot be revoked.** The session is a stateless JWT ([auth-0002](decisions/auth-0002-cookie-session.md)): a stolen token stays valid until it expires, and there is no logout-everywhere, no per-session audit, and no way to eject an attacker. Production backs sessions with a database table carrying `revoked_at`. Argued at length in [auth-0002](decisions/auth-0002-cookie-session.md) and [thesis/robo-de-sesion.md](thesis/robo-de-sesion.md); the same reasoning covers verification and password-reset tokens ([auth-0003](decisions/auth-0003-preregistration-shell-mitigation.md)).

**Rate limiting is in-process.** Once implemented ([phases/phase-5.md](phases/phase-5.md) Slice 13), the limiter's default storage is per-process memory. With N replicas that grants N times the intended limit, so the protection *weakens as you scale* — the opposite of the desired property. Production backs it with Redis.

**No automated dependency or container scanning**, no SAST/DAST in CI, and no penetration testing. Renovate ([phases/phase-5.md](phases/phase-5.md) Slice 11) keeps dependencies current, which is not the same as knowing whether any of them is vulnerable today.

## Landmines specific to this codebase

Generic advice stops being useful here. These three would break in non-obvious ways, and they are properties of *this* system rather than of scale in general.

**The scheduler cannot be replicated.** `supercronic` runs inside a single container. Run two, and both fire `refresh_reve` on the same schedule against an API capped at **5 requests per hour** — the budget is exhausted instantly and the ETL enters a permanent rate-limited loop. Any move to multiple hosts requires a single explicitly-unreplicated scheduler, leader election, or a job queue with a distributed lock.

**The ETL cursor row can race.** `reve_etl_cursor` holds one row per endpoint, read-modify-written on every tick. Two concurrent runs corrupt the refresh watermark — the exact field whose loss produced the July 2026 tariff gap. This is reachable *today*, without any scaling: running `refresh_reve` by hand while the hourly cron ticks is two concurrent writers. A Postgres advisory lock taken at the top of the tick fixes it. *Scheduled: [plan.md](plan.md) Phase 13.*

**Charging-point availability is not modelled** ([be-0002](decisions/be-0002-availability-not-modelled.md)). Points are shown as available with a disclaimer. A real product needs live status, which means either OCPI integration with each CPO or a status feed REVE does not offer — a data-access problem, not an engineering one.

## Legal and compliance

**GDPR obligations are unaddressed.** The application stores personal data of EU subjects (`users`, `oauth_account`: email, name, provider identity). Real users make the following binding rather than optional: a published privacy policy, a lawful basis for processing, data-processing agreements with each processor (Hetzner, Resend, Google), a defined retention policy, a working right-to-erasure path, data-portability export, and breach notification within 72 hours.

None of this exists, and the erasure path is not merely a missing endpoint — deleting a user has to reckon with what happens to their sessions, bookings and ledger rows.

*Scheduled as thesis content: [plan.md](plan.md) Phase 14, alongside the business chapter.*

**No terms of service, and no cookie/consent notice.** The session cookie is strictly necessary so it needs no consent banner under EU rules, but that conclusion should be documented rather than assumed.

## Process

**One developer, no review.** Every change is written and approved by the same person. Branch protection ([phases/phase-5.md](phases/phase-5.md) Slice 9) enforces that changes arrive through a pull request with green CI, which catches mechanical errors but not design ones.

**No load testing.** No measurement exists of where this stack saturates — concurrent connections, map-viewport query cost, or the RAM contention between a Vite build and Postgres during a deploy. The Phase 14 chapter argues where the box breaks first; nothing has measured it.

**Test coverage is not enforced.** Phase 13 targets ≥70% on `services/`; CI does not gate on coverage today.
