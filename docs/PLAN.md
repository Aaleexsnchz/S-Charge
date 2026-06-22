# EV Charging Point Management App — Plan

## Context

Master's thesis (IoT): a **PWA** for managing EV charging. It unifies, under one app, what is today fragmented across each operator's own application, and improves on the Spanish government's REVE app (which only lets you view points and plan a route). It seeds the real Spanish network from the **REVE API** (locations, EVSEs, connectors, tariffs) and adds the functionality REVE lacks: private charging points with paid use, bookings, price/time charging optimisation, charge simulation, and (candidate) AI/agent features. Alongside the app, the thesis includes a brief business plan, a deployment/scaling/profitability strategy, and a roadmap (including the transition to a native mobile app).

**The thesis pillar is the application itself** — its conception, design, full-stack development, deployment, and viability. The charging optimiser and the AI/agent features are *value-add functionalities of the app*, not separate cores standing apart from it.

**Goal:** a real, deployed, usable application to demo at thesis defense, publicly accessible.

---

## Data strategy

| Source | Role | Provides |
| --- | --- | --- |
| **REVE API** | Real-world map layer (seed source) | Spanish CPO catalogue (locations, EVSEs, connectors), tariffs, OCPI 2.2.1 metadata. Seeded once into Postgres; live availability is simulated by a lightweight synthetic model (not grounded in external data), not relayed. |
| **REE / PVPC** | Hourly electricity prices (Spain) | Drives owner dynamic pricing (PVPC + margin) and the smart home-charging optimiser. Public API, no token. |
| **Vehicle catalogue** | Simulation input | Curated table of common EVs in Spain (battery capacity, max AC/DC charging power) seeded from public spec sheets. |
| **User-generated** | Platform contribution | Private charging points with public/private toggle, paid use, bookings, recorded sessions |

REVE provides the real network presence; PVPC provides the economics; user-generated points provide the platform contribution.

> **ACN-Data was dropped (2026-06-21).** Caltech's historical-session dataset was originally to calibrate occupancy/session realism. It stayed internal-only, never landed (blocked on a token, only a smoke test ran), and added nothing user-facing. It now survives only as a documented *road not taken* in the thesis — see [thesis/indice.md](thesis/indice.md). Live availability is now a simple synthetic model, claimed only as illustrative.

**Product framing (2026-06-12, updated 2026-06-21).** Two user roles. **Drivers** find points on the map, book them, navigate via Google Maps, simulate a charge for their car model before plugging in, charge their own point on an economically optimised schedule, pay for public sessions from a simulated wallet, and review their real session history. **Owners** register points for private or public use, price public ones (PVPC + margin, or fixed), and manage/monitor their points' usage and revenue.

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
  │  tariffs · vehicles · prices     │          │   fetch_pvpc.py       │
  └──────────────────────────────────┘         └───────────────────────┘
```

- **REVE: seeded into Postgres via one-shot ETL.** REVE's public API caps at 5 requests/hour, which makes a live-mirror architecture impractical. We bootstrap the catalogue once into Postgres and own the data going forward.
- **Live availability is simulated** by a lightweight synthetic model (Phase 4), not relayed from REVE and not grounded in any external dataset — presented as illustrative only.
- **User-contributed points** stored in `charging_points` alongside REVE-seeded points, distinguished by a `source` column.
- **OCPI 2.2.1-aligned schema** so future commercial CPO agreements plug in by extending the `source` enum.

---

## Features

1. **Map** — REVE + public user points with filters (availability, connector, price), Google Maps redirect
2. **Point detail** — real data from REVE + booking
3. **Pre-charge simulation** — driver picks car model + connector (+ SoC range): predicted duration, energy, cost (spec/physics-based: power = min(vehicle, connector), AC/DC-aware taper)
4. **Smart home charging** — at an owned point: cheapest charging schedule for tonight given PVPC hourly prices and departure time
5. **Private charging points + paid use** — user-registered, private or public; public ones priced as PVPC + margin or fixed; drivers pay from a simulated wallet/ledger, owners credited (real payment processing: stretch)
6. **Driver dashboard** — bookings + recorded session history (energy, duration, cost) + wallet balance/transactions
7. **Owner dashboard** — per-point usage stats (sessions, energy, revenue from the ledger) and management
8. **AI/agent assistant** — *candidate, time-gated* — value-add features over the app's own APIs (see [ideas-backlog.md](ideas-backlog.md))

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

**Revision (2026-06-16):** REVE operational-status mirror dropped. *Operational status* (working/broken) is now assumed always-operational and not modelled; *availability* (free/in use) becomes a `status` column on the EVSE (OCPI value, simulated in Phase 4), and the map's `aggregate_status` is now available/occupied/unknown. A post-seed incremental refresh (`refresh_reve.py`) keeps tariffs fresh under the rate cap. Pricing strategy fixed: serve the real REVE tariff; where none exists, estimate `PVPC + margin` (recommended default AC +0.22 / DC +0.32 €/kWh, owner-overridable). PVPC history backfilled. See [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md).

**Revision (2026-06-21) — scope pivot: the application *is* the thesis.** ACN-Data is dropped entirely (code deleted; kept only as a documented road-not-taken). The thesis core is no longer a novel data combination or a real-session-grounded simulation — it is the **application itself**: a unified, multi-provider EV-charging PWA that improves on REVE, end-to-end built, deployed, and argued viable. The charging optimiser and the (candidate) AI/agent features are value-add functionalities, not separate cores. Concrete changes below: **Phase 3 dropped**; **Phase 4** loses ACN distribution-fitting (occupancy becomes a simple synthetic model) and is reframed as a feature, not "the academic core"; **Phase 5** gains a simulated **wallet/ledger** for paid use; **Phase 6** gains a deployment & scaling strategy; **Phase 7** gains business-plan, deployment and roadmap chapters; **new Phase 8** is a time-gated AI assistant. The thesis outline lives in [thesis/indice.md](thesis/indice.md); deferred ideas in [ideas-backlog.md](ideas-backlog.md).

Slice-by-slice record: [phases](phases).

### Phase 1 — Foundation (22–28h) — done

Docker Compose, FastAPI + Postgres + Alembic, auth via `fastapi-users` (email/password + Google OAuth) with Argon2id, single HttpOnly session cookie, email verification + password reset via Resend, stdout JSON audit logging, plus the React + Vite + MUI frontend scaffold with auth pages and PWA installability.

**Done when:**

- [x] Email/password auth: register, login (gated on verification), `/api/users/me`, logout, audit logging
- [x] Email verification + password reset emails via Resend
- [x] Google OAuth end-to-end via `httpx-oauth`; first-time users auto-provisioned; existing accounts linkable
- [x] Frontend scaffold serves the six auth pages (login, register, check-email, verify-email, forgot-password, reset-password); Spanish copy; PWA installable on iOS Safari and Chrome

### Phase 2 — REVE seed + Map (25–30h) — done

REVE seeded into Postgres via cursor-based ETL under the 5 req/hr public-API cap. Frontend renders a map of Spanish charging points with filters and a detail view.

**Done when:**

- [x] REVE seed runs unattended via cron; full-Spain bootstrap completes in ~12 days
- [x] `/api/points` and `/api/points/{id}` serve seeded points
- [x] Map renders with filters (availability, connector, price band), point detail, Google Maps "Navegar" deep link
- [x] Tested on real iPhone + Android

### Phase 3 — ACN import + internal analysis — DROPPED (2026-06-21)

**Dropped in the scope pivot.** ACN-Data (Caltech's historical-session dataset, originally to calibrate occupancy/session realism) added nothing user-facing, never landed (blocked on a token; only a smoke test ran), and is no longer part of the thesis core. The phase doc and all ACN code were deleted; ACN survives only as a documented road-not-taken in [thesis/indice.md](thesis/indice.md).

### Phase 4 — Simulation + Algorithm (28–36h)

Vehicle catalogue, PVPC price ingest, per-car pre-charge simulation, smart home-charging optimiser, and a lightweight synthetic availability model. A **value-add feature** of the app — the optimiser deepens the product and gives the thesis an evaluable algorithm chapter, but it is not the thesis on its own.

**Done when:**

- [x] `vehicles` table seeded with ~25–30 common Spanish-market EVs (battery kWh, max AC/DC kW)
- [x] PVPC hourly prices ingested daily from REE's public API (cron, same tick pattern as REVE)
- [ ] Lightweight synthetic availability model drives the map's `aggregate_status` (illustrative only, not grounded in external data)
- [ ] `/api/simulate`: car model + connector (+ SoC range) → predicted duration, energy, cost (REVE tariff or owner price); spec/physics-based (power = min(vehicle, connector), AC/DC taper)
- [ ] `/api/recommend`: owned point + departure time + energy needed → cheapest PVPC charging schedule + alternatives
- [ ] Simulation UI shows the predicted session; 1–2 page algorithm write-up reusable in the thesis

### Phase 5 — Private points, Bookings, Sessions + Wallet (30–40h)

Private point CRUD with owner pricing, bookings, session recording, driver history, owner dashboard, and a **simulated wallet/ledger** for paid use. Re-expanded 2026-06-12 (owner per-point stats are core); 2026-06-21 adds the wallet (real payment processing stays stretch).

**Done when:**

- [ ] Private point creation works end-to-end; public/private toggle controls map visibility
- [ ] Public points priced as PVPC + margin (live) or fixed €/kWh, owner's choice
- [ ] Booking conflict detection rejects overlaps; user can view/cancel bookings
- [ ] Completed bookings and home smart-charges record a session (energy, duration, cost); driver sees history in `/sessions`
- [ ] Wallet/ledger: per-user balance, top-up (simulated), a completed paid session debits the driver at the point's price and credits the owner; both see the transaction history
- [ ] Owner dashboard: per-point sessions, energy delivered, revenue (sourced from the ledger)

### Phase 6 — Polish + Deployment (22–28h)

Responsive QA, error states, deploy, tests, and a written deployment & scaling strategy.

**Done when:**

- [ ] All pages tested on real phone
- [ ] Every API call has loading/error/empty states
- [ ] Backend tests pass with ≥70% coverage on `services/`
- [ ] Deployed at real HTTPS domain
- [ ] PWA installable from production on iOS + Android
- [ ] At least one external user registers + uses the app
- [ ] Deployment & scaling strategy written: architecture-for-scale + cost/unit-economics model (the live deploy stays single-instance; the strategy is the thesis artifact)

### Phase 7 — Thesis writing (45–65h)

Document, diagram, defend. Includes the business and strategy chapters that elevate the work beyond a pure implementation.

**Done when:**

- [ ] Full draft: intro, SoTA, architecture, data, implementation, results, conclusions
- [ ] Architecture + ER diagrams, UI screenshots included
- [ ] Algorithm chapter: formulation, pseudocode, evaluation of the charging optimiser
- [ ] Business plan & viability chapter; deployment/scaling chapter; future-roadmap chapter (incl. native mobile)
- [ ] ≥20 references
- [ ] Defense slides (15–20) + demo plan
- [ ] Tutor approves final version

### Phase 8 — AI/agent assistant (candidate, time-gated)

A value-add feature, **not a pillar** — built only after Phase 6 ships and only if time allows; the defense demo must never depend on it. Concrete ideas (NL charging/trip assistant, explain-the-schedule, conversational point search, etc.) live in [ideas-backlog.md](ideas-backlog.md); depth is decided when reached, against remaining hours.

---

## Stretch goals

Only after Phase 6 (deployed, demo-ready) and only if hours remain. None of these are committed scope; the defense demo must not depend on them.

- **Route optimisation (~10–15h, minimal version).** Given origin/destination, fetch the route polyline from a free routing API (OSRM / OpenRouteService), corridor-query seeded points along it, rank candidate stops by detour + price + Phase 4 predicted session. No consumption modelling, no custom routing engine — those would be 30–40h and are out of scope for this timeline.
- **Real payments.** Replace the simulated wallet/ledger with a real processor (e.g. Stripe test mode) + commission tracking on the owner dashboard.
- **AI/agent assistant.** Tracked as Phase 8; the full idea list is in [ideas-backlog.md](ideas-backlog.md).

---

## What makes this thesis-worthy

1. **The application itself** — a real, unified, multi-provider EV-charging PWA that improves on the government REVE app (which only views points and plans routes), built end-to-end: conception, design, full-stack implementation, deployment.
2. **Platform model** — user-contributed charging infrastructure with paid use, bookings and a wallet/ledger economy.
3. **Charging optimiser** — a price/time optimisation algorithm over real PVPC prices, with evaluable output (a value-add feature, written up in the algorithm chapter).
4. **Deployed and usable** — at a real HTTPS URL, installable as a PWA, with at least one real external user.
5. **Business & viability** — a brief business plan, a deployment/scaling/profitability strategy, and a roadmap (incl. native mobile) that argue the product beyond the prototype.
6. **Academically honest** — explicit about what is real vs. simulated (e.g. availability is illustrative, payments are a simulated ledger), and about the road not taken (ACN-Data).
7. **Candidate AI/agent layer** — natural-language/agent features over the app's own APIs as a differentiator (time-gated; the defense never depends on it).
