# Electricity prices (PVPC)

**Status:** ✅ Implemented · **Shipped in** [Phase 3](../plan/phases/phase-3.md)

Spain's regulated hourly electricity price, ingested daily from REE's public API. It is what makes the economics of the app real: it prices simulated sessions where no tariff exists, it will price owner points as `PVPC + margin`, and it is the curve the optimiser schedules against.

## Today

- **Backend** — `ReeClient` against `apidatos.ree.es` (PVPC indicator 1001, no token). `scripts/fetch_pvpc.py` fetches a yesterday/today/tomorrow window and is safe to re-run; tomorrow publishes around 20:15 CET, and REE answers 500 for a day that is not published yet, which the script treats as "not yet" rather than an error. `electricity_prices` stores one row per hour. `GET /api/prices/today` (and `?day=`, Madrid-local) serves the curve. History is backfilled from 2026-01-01.
- **Scheduling** — runs in the `scheduler` container in production ([Phase 5](../plan/phases/phase-5.md)); still on the laptop's crontab until the server exists.

## Related

The price cascade — real REVE tariff → owner price → `PVPC + margin` (defaults AC +0.22 / DC +0.32 €/kWh) — is described in [the thesis](../thesis/S-Charge-TFM.pdf).
