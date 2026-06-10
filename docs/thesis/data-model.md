---
status: draft (thesis writeup, concept-level)
---

# Data model — CPOs, Charging Points, EVSEs, Connectors

The real-world charging-network catalogue ships from the [REVE API](https://www.mapareve.es), Spain's public OCPI 2.2.1 directory. The schema mirrors OCPI's four-level hierarchy: one operator runs many sites, each site has many physical stalls, each stall has one or two plugs. Live availability is deliberately not relayed (REVE's 5 req/hr public-API cap makes a live proxy impractical) — Phase 4 layers ACN-driven simulation on top of the static catalogue, which is owned in Postgres after the initial seed.

## The hierarchy

```text
Cpo                   the operator company (Iberdrola, Endesa X, Wenea, ...)
 └── ChargingPoint    a physical site on the map (lat/lng, address, opening hours)
      └── Evse        one parking stall within a charging point
           └── Connector   the actual plug (Type 2, CCS, CHAdeMO) + power + tariff
```

In the REVE catalogue snapshot at seed time, Spain has 142 CPOs across roughly 13,700 charging points, which expand to about 42,000 EVSEs and 47,000 connectors — a charging point averages three EVSEs, and most EVSEs carry a single connector.

## CPO — Charge Point Operator

The legal entity running the hardware. Identified by an OCPI `party_id` (a short alphanumeric code like `"IBE"`) plus a Spanish `cif` business tax ID. Stable identifiers — operators don't churn — which is why `/cpos` is the lightest endpoint and exhausts in two pages.

## Charging Point

A physical site. The "station" the driver navigates to. Carries the data that matters for the map and the detail screen: latitude, longitude, address, parking type, opening hours (with the `opening_24_7` shortcut), facilities (food, restroom, wifi). One CPO owns each charging point — the FK `charging_points.party_id → cpos.party_id` links to the operator's catalogue row.

A naming choice worth recording: OCPI calls these "**locations**" (which is why the REVE endpoint is `/locations`). The app schema renames to `charging_points` because that reads more naturally in code paths like `GET /api/points` and `usePoint(id)` than the more abstract OCPI term. The mirror schema preserves the OCPI semantics; only the table name shifts.

The `source` column distinguishes REVE-seeded points (`reve_seed`) from user-contributed private points (Phase 5, `user`). Sharing the table keeps the map query single-source — both kinds of points land in the same response shape.

## EVSE — Electric Vehicle Supply Equipment

One physical stall within a charging point. A site with four parking spots has four EVSE rows. EVSEs are the unit of operational status — the `is_operational` boolean populated by the bulk `/evses/operational_status` endpoint lives here. That boolean is the only availability signal the public API exposes: the per-EVSE `/evses/{evse_id}` endpoint returns static data only (capabilities, floor level, physical reference — a near-subset of what `/locations` already nests), with no real-time OCPI status enum, so at ~42,000 EVSEs nationwide the 5 req/hr cap rules out per-EVSE fetching with nothing to gain from it. The marker colour on the map is computed as a per-charging-point `aggregate_status` rollup of those booleans (operational / partial / inoperative / unknown).

## Connector

The actual plug, with the technical characteristics drivers filter on: `standard` (Type 2, CCS, CHAdeMO, etc.), `power_type` (AC single-phase, AC three-phase, DC), and the trio of `max_electric_power`, `max_voltage`, `max_amperage`. A nullable FK `connectors.tariff_id` links to the `tariffs` table — REVE returns tariffs via a separate endpoint (`/connectors/tariffs`), which is why tariff data lags behind the rest of the catalogue during the seed.

## Why mirror instead of proxy

The architectural choice — own the catalogue in Postgres rather than live-proxy REVE — is driven entirely by the rate cap. Five requests per hour is below the floor of any real-time UX; a cold map load would consume the entire hour's allowance. Mirroring also lets the project add user-contributed private points to the same table, evolve the schema without coordinating with the upstream, and stay functional during REVE outages. The cost is a 12-day initial seed and a once-a-day catalogue refresh job — both happen unattended in a cron tick. See [PLAN.md](../PLAN.md) for the architecture diagram and [phases/phase-2.md](../phases/phase-2.md) for the seed slice.
