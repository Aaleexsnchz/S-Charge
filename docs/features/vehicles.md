# Vehicle catalogue

**Status:** ✅ Implemented · **Shipped in** [Phase 3](../plan/phases/phase-3.md)

A curated table of EVs common in the Spanish market, used as the input to charge simulation: usable battery capacity and maximum AC/DC charging power per model.

## Today

- **Backend** — `vehicles` table seeded from public spec sheets by `scripts/seed_vehicles.py` (31 models, idempotent upsert keyed on make + model). `GET /api/vehicles` serves the catalogue ordered for a picker.
- **Frontend** — the vehicle selector inside the simulation dialog.

Curated rather than sourced from an API: no free, complete, licence-clean EV spec API exists for the Spanish market, and 30 models cover the fleet a demo will ever show.
