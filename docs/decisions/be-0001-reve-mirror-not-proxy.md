---
id: be-0001
status: accepted
phase: 2
date: 2026-05
---

# be-0001: Mirror the REVE catalogue into Postgres instead of proxying it

**Decision.** The Spanish charging-point catalogue is **copied into our own Postgres** by a cursor-based ETL and served from there. The application never calls the [REVE API](https://www.mapareve.es) while handling a user request. The schema mirrors OCPI 2.2.1 (CPO → charging point → EVSE → connector → tariff), and a `source` column distinguishes REVE-seeded rows from user-registered ones.

**Rationale.** REVE's public API allows **5 requests per hour**. That single number decides the architecture: a cold load of the map would consume an entire hour's quota, so a live proxy cannot serve even one user, let alone a demo. Owning the data also buys three things a proxy could not: user-contributed points live in the same tables and the same query, the schema can evolve without the provider's cooperation, and the app keeps working when REVE is down — which it measurably is (a 504 regression on wide refresh windows has been open since 2026-07-08).

**Consequences.**

- **The initial seed costs ~12 days** of unattended cron ticks. This is the single most expensive artifact in the project: it must never be re-run to populate an environment. Production and any rebuilt environment bootstrap from a `pg_dump` seed archive instead ([operations.md](../operations.md)).
- **The catalogue is a snapshot with a known refresh policy, not a live mirror.** Only `/connectors/tariffs` is refreshed after the seed; new stations added to REVE after the snapshot do not appear. Accepted deliberately — see [thesis/precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).
- The refresh watermark is a **correctness-critical value**. Because the seed is paginated across days, the first refresh must start from `min(tariffs.last_refreshed_at)`, not the seed's `completed_at`, or tariffs that changed mid-seed are silently skipped.
- A stalled refresh cannot be fully recovered: on a 504 with a stale watermark the ETL jumps the watermark to recent and the intervening window is skipped permanently, by design, because re-pulling it costs days of quota.
- Storage and backup become our responsibility, including offsite copies of an artifact that cannot be regenerated cheaply.

**Rejected alternatives.**

- *Live proxy to REVE per request.* Impossible under 5 req/hr, and it would make the app's availability a function of REVE's.
- *Proxy with an aggressive cache.* Merely relocates the mirror into a cache with worse guarantees: no schema control, no place to put user-contributed points, and cold caches still exceed the quota.
- *Scrape the public map front-end instead of the API.* Higher volume, no rate limit in theory — but no stable contract, and legally and academically indefensible for a thesis.
- *A smaller geographic scope (one region) to fit the quota.* Would have made the seed cheap, at the cost of the product's central claim: a nationwide unified view.

**References.**

- [thesis/modelo-de-datos.md](../thesis/modelo-de-datos.md) — the OCPI hierarchy as mirrored, in Spanish.
- [thesis/planificacion-de-siembra.md](../thesis/planificacion-de-siembra.md) — seed scheduling and the per-tick contract.
- [be-0002](be-0002-availability-not-modelled.md) — why the one field this catalogue cannot supply is left unmodelled.
