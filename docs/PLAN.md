# EV Charging Point Management App — Plan

## Context

Master's thesis (IoT): a **PWA** for managing EV charging. Combines the **REVE API** (real Spanish charging network: location, occupation, price) with **ACN-Data** (real historical sessions from Caltech, for analytics/simulation/algorithms). Users can also register their own private charging points.

**Goal:** a real, deployed, usable application to demo at thesis defense, publicly accessible.

---

## Data strategy

| Source | Role | Provides |
| --- | --- | --- |
| **REVE API** | Real-world map layer (seed source) | Spanish CPO catalogue (locations, EVSEs, connectors), tariffs, OCPI 2.2.1 metadata. Seeded once into Postgres; live availability is simulated, not relayed. |
| **ACN-Data** | Modelling dataset (**internal only — never shown in the app**) | Real historical sessions used to fit the distributions behind occupancy simulation and session realism. Analysed in a thesis notebook, not a user-facing screen. |
| **REE / PVPC** | Hourly electricity prices (Spain) | Drives owner dynamic pricing (PVPC + margin) and the smart home-charging optimiser. Public API, no token. |
| **Vehicle catalogue** | Simulation input | Curated table of common EVs in Spain (battery capacity, max AC/DC charging power) seeded from public spec sheets. |
| **User-generated** | Platform contribution | Private charging points with public/private toggle, bookings, recorded sessions |

REVE provides the real network presence; ACN provides the behavioural realism REVE lacks; PVPC provides the economics.

**Product framing (2026-06-12).** Two user roles. **Drivers** find points on the map, book them, navigate via Google Maps, simulate a charge for their car model before plugging in, charge their own point on an economically optimised schedule, and review their real session history. **Owners** register points for private or public use, price public ones (PVPC + margin, or fixed), and manage/monitor their points' usage. ACN data powers the simulation machinery behind all of this but is never user-facing content.

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

1. **Map** — REVE + public user points with filters (availability, connector, price), Google Maps redirect
2. **Point detail** — real data from REVE + booking
3. **Pre-charge simulation** — driver picks car model + connector (+ SoC range): predicted duration, energy, cost; session realism calibrated on ACN distributions
4. **Smart home charging** — at an owned point: cheapest charging schedule for tonight given PVPC hourly prices and departure time
5. **Private charging points** — user-registered, private or public; public ones priced as PVPC + margin or fixed (commission tracking: stretch)
6. **Driver dashboard** — bookings + recorded session history (energy, duration, cost)
7. **Owner dashboard** — per-point usage stats (sessions, energy, revenue) and management
8. **ACN analysis notebook** — thesis material (dataset validation + conclusions), outside the app

---

## Key screens

| Route | Purpose |
| --- | --- |
| `/` | Dashboard |
| `/map` | Live map (REVE) |
| `/points/:id` | Point detail + booking |
| `/sessions` | Driver session history |
| `/simulate` | Pre-charge simulation (car + point) |
| `/my-points` + `/new` | Private point management + owner stats |
| `/bookings` | Reservations |
| `/profile`, `/login` | Auth |

---

## Development phases

Total: **~195–260h** over 12 weeks (~16–22h/week). Each phase has a brief description and acceptance criteria — task plans get written into `phases/phase-N.md` *when starting the phase*, not before.

**Pacing check (2026-06-11):** ~9 weeks to the defense (~mid-August). Remaining work (rest of Phase 2 + Phases 3–7) is ~165–225h, i.e. **19–25h/week** — above the original assumption, with no slack. Mitigations baked in below: thesis chapters written per slice (shrinks the Phase 7 tail), and anything in [Stretch goals](#stretch-goals) only after Phase 6 ships. If anything slips, cut Phase 5 scope — never Phases 4, 6, or 7.

**Revision (2026-06-12):** product refocus — ACN demoted to internal modelling data (Phase 3 shrinks: notebook instead of dashboard), Phase 4 gains the vehicle catalogue + PVPC ingest, Phase 5 regains owner per-point stats and adds session recording. Net scope roughly unchanged; Phases 2–3 are tracking well under their original estimates, which absorbs the additions.

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

### Phase 3 — ACN import + internal analysis (18–24h)

ETL pipeline for ACN-Data plus a thesis analysis notebook. Reframed 2026-06-12: ACN is internal modelling data, so no user-facing analytics screen — the dashboard originally planned here was built, then deliberately removed in favour of a notebook (see phase doc).

**Done when:**

- ACN imported; row counts match source
- Core tables populated and indexed
- Analysis notebook (energy, arrivals heatmap, cross-site) produces thesis figures + conclusions
- Data validation doc (nulls, gaps, ranges) written

### Phase 4 — Simulation + Algorithm (40–50h)

Vehicle catalogue, PVPC price ingest, distribution fitting, per-car simulation, smart home-charging optimiser. **The academic core of the thesis.**

**Done when:**

- `vehicles` table seeded with ~25–30 common Spanish-market EVs (battery kWh, max AC/DC kW)
- PVPC hourly prices ingested daily from REE's public API (cron, same tick pattern as REVE)
- Distribution fitting on ACN produces occupancy/arrival parameters; simulated availability drives map status
- `/api/simulate`: car model + connector (+ SoC range) → predicted duration, energy, cost (REVE tariff or owner price)
- `/api/recommend`: owned point + departure time + energy needed → cheapest PVPC charging schedule + alternatives
- Simulation UI shows the predicted session; 1–2 page algorithm write-up reusable in the thesis

### Phase 5 — Private points, Bookings + Sessions (26–34h)

Private point CRUD with owner pricing, bookings, session recording, driver history, owner dashboard. Re-expanded 2026-06-12: owner per-point stats are core product (commission tracking stays stretch).

**Done when:**

- Private point creation works end-to-end; public/private toggle controls map visibility
- Public points priced as PVPC + margin (live) or fixed €/kWh, owner's choice
- Booking conflict detection rejects overlaps; user can view/cancel bookings
- Completed bookings and home smart-charges record a session (energy, duration, cost); driver sees history in `/sessions`
- Owner dashboard: per-point sessions, energy delivered, revenue

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
