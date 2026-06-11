# EV Charging Point Management App — Plan

## Context

Master's thesis (IoT): a **PWA** for managing EV charging. Combines the **REVE API** (real Spanish charging network: location, occupation, price) with **ACN-Data** (real historical sessions from Caltech, for analytics/simulation/algorithms). Users can also register their own private charging points.

**Goal:** a real, deployed, usable application to demo at thesis defense, publicly accessible.

---

## Data strategy

| Source | Role | Provides |
| --- | --- | --- |
| **REVE API** | Real-world map layer (seed source) | Spanish CPO catalogue (locations, EVSEs, connectors), tariffs, OCPI 2.2.1 metadata. Seeded once into Postgres; live availability is simulated, not relayed. |
| **ACN-Data** | Analytics + simulation backbone | Real historical sessions, charging profiles |
| **User-generated** | Platform contribution | Private charging points with public/private toggle |

REVE provides the real network presence; ACN provides the behavioural data REVE lacks.

---

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | React + Vite + TypeScript + MUI v7 |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| ORM / Migrations | SQLAlchemy 2.0 + Alembic |
| Containers | Docker Compose |

---

## Architecture

```text
  ┌──────────────────────────────────┐
  │  PWA Frontend (frontend/)        │
  │  React + Vite + MUI v7           │
  └────────────────┬─────────────────┘
                   │ HTTPS, /api/*
                   ▼
  ┌──────────────────────────────────┐
  │  FastAPI Backend (backend/)      │
  │  routers → services → models     │
  └────────────────┬─────────────────┘
                   │ async (asyncpg)
                   ▼
  ┌──────────────────────────────────┐         ┌───────────────────────┐
  │  PostgreSQL                      │ ◄─────── │  ETL scripts          │
  │  users · bookings                │ one-shot │  (backend/scripts/)   │
  │  charging_points · connectors    │  writes  │   seed_reve.py        │
  │  tariffs · evse_status · acn_*   │          │   import_acn.py       │
  └──────────────────────────────────┘         └───────────────────────┘
```

- **REVE: seeded into Postgres via one-shot ETL.** REVE's public API caps at 5 requests/hour, which makes a live-mirror architecture impractical. We bootstrap the catalogue once into Postgres and own the data going forward.
- **Live availability is simulated**, not relayed from REVE — driven by ACN-Data utilisation distributions in Phase 4.
- **ACN: bulk-imported once via ETL** — same pattern as REVE seed.
- **User-contributed points** stored in `charging_points` alongside REVE-seeded points, distinguished by a `source` column.
- **OCPI 2.2.1-aligned schema** so future commercial CPO agreements plug in by extending the `source` enum.

---

## Features

1. **Map** — REVE points with filters (availability, connector, price), Google Maps redirect
2. **Point detail** — real data from REVE + simulated booking
3. **Session analytics** — ACN-powered visualisations (energy, heatmap, utilisation, cross-site)
4. **Pre-charge simulation** — predicted duration/energy/cost from ACN distributions
5. **Smart charging algorithm** — recommended start time given constraints
6. **Private charging points** — user-registered, public/private toggle (commission tracking: stretch)
7. **User dashboard** — sessions, bookings, owned points, cost history
8. **System analytics** (admin) — aggregate stats across the platform

---

## Key screens

| Route | Purpose |
| --- | --- |
| `/` | Dashboard |
| `/map` | Live map (REVE) |
| `/points/:id` | Point detail + booking |
| `/sessions` | User session history |
| `/simulate` | Pre-charge simulation |
| `/statistics` | ACN analytics dashboard |
| `/my-points` + `/new` | Private point management |
| `/bookings` | Reservations |
| `/profile`, `/login` | Auth |

---

## Development phases

Total: **~195–260h** over 12 weeks (~16–22h/week). Each phase has a brief description and acceptance criteria — task plans get written into `phases/phase-N.md` *when starting the phase*, not before.

**Pacing check (2026-06-11):** ~9 weeks to the defense (~mid-August). Remaining work (rest of Phase 2 + Phases 3–7) is ~165–225h, i.e. **19–25h/week** — above the original assumption, with no slack. Mitigations baked in below: Phase 5 trimmed to its demo-critical core, thesis chapters written per slice (shrinks the Phase 7 tail), and anything in [Stretch goals](#stretch-goals) only after Phase 6 ships. If anything slips, cut Phase 5 scope — never Phases 4, 6, or 7.

Slice-by-slice record: [phases](phases).

### Phase 1 — Foundation (22–28h) — done

Docker Compose, FastAPI + Postgres + Alembic, auth via `fastapi-users` (email/password + Google OAuth) with Argon2id, single HttpOnly session cookie, email verification + password reset via Resend, stdout JSON audit logging, plus the React + Vite + MUI frontend scaffold with auth pages and PWA installability.

**Done when:**

- [x] Email/password auth: register, login (gated on verification), `/api/users/me`, logout, audit logging
- [x] Email verification + password reset emails via Resend
- [x] Google OAuth end-to-end via `httpx-oauth`; first-time users auto-provisioned; existing accounts linkable
- [x] Frontend scaffold serves the six auth pages (login, register, check-email, verify-email, forgot-password, reset-password); Spanish copy; PWA installable on iOS Safari and Chrome

### Phase 2 — REVE seed + Map (25–30h)

REVE seeded into Postgres via cursor-based ETL under the 5 req/hr public-API cap. Frontend renders a map of Spanish charging points with filters and a detail view.

**Done when:**

- REVE seed runs unattended via cron; full-Spain bootstrap completes in ~12 days
- `/api/points` and `/api/points/{id}` serve seeded points
- Map renders with filters (availability, connector, price band), point detail, Google Maps "Navegar" deep link
- Tested on real iPhone + Android

### Phase 3 — ACN import + Analytics (30–40h)

ETL pipeline for ACN-Data, aggregation endpoints, charts dashboard.

**Done when:**

- ACN imported; row counts match source
- Core tables populated and indexed
- Statistics endpoints return aggregations
- Charts dashboard renders the key analytics views
- Data validation doc (nulls, gaps, ranges) written

### Phase 4 — Simulation + Algorithm (35–45h)

Distribution fitting, simulation, optimisation, session history. **The academic core of the thesis.**

**Done when:**

- Distribution fitting produces per-station parameters
- `/api/simulate` returns predicted duration, energy, cost
- Simulation UI shows predicted session chart
- `/api/recommend` returns optimal start time + alternatives
- 1–2 page algorithm write-up reusable in the thesis

### Phase 5 — Private points + Bookings (20–28h)

Private point CRUD, bookings, public/private toggle, owner dashboard. Trimmed 2026-06-11 to the demo-critical core; revenue/utilisation/commission analytics moved to [Stretch goals](#stretch-goals).

**Done when:**

- Private point creation works end-to-end
- Public/private toggle controls map visibility
- Booking conflict detection rejects overlaps
- User can view/cancel bookings
- Owner dashboard lists upcoming and past bookings for owned points

### Phase 6 — Polish + Deployment (20–25h)

Responsive QA, error states, deploy, tests.

**Done when:**

- All pages tested on real phone
- Every API call has loading/error/empty states
- Backend tests pass with ≥70% coverage on `services/`
- Deployed at real HTTPS domain
- PWA installable from production on iOS + Android
- At least one external user registers + uses the app

### Phase 7 — Thesis writing (40–60h)

Document, diagram, defend.

**Done when:**

- Full draft: intro, SoTA, architecture, data, implementation, results, conclusions
- Architecture + ER diagrams, UI screenshots included
- Algorithm chapter: formulation, pseudocode, evaluation on ACN
- ≥20 references
- Defense slides (15–20) + demo plan
- Tutor approves final version

---

## Stretch goals

Only after Phase 6 (deployed, demo-ready) and only if hours remain. None of these are committed scope; the defense demo must not depend on them.

- **Route optimisation (~10–15h, minimal version).** Given origin/destination, fetch the route polyline from a free routing API (OSRM / OpenRouteService), corridor-query seeded points along it, rank candidate stops by detour + price + Phase 4 predicted session. No consumption modelling, no custom routing engine — those would be 30–40h and are out of scope for this timeline.
- **Owner analytics (from Phase 5 trim).** Revenue, utilisation, and commission tracking on the owner dashboard.

---

## What makes this thesis-worthy

1. Two real data sources combined in a novel way (REVE + ACN)
2. Real statistical simulation layer grounded in real sessions
3. Optimisation algorithm with evaluable output
4. Platform model (user-contributed infrastructure)
5. Actually deployed at a real URL, installable as PWA
6. Academically honest about what is real vs. simulated
