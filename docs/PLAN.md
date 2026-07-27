# EV Charging Point Management App — Plan

## Context

Master's thesis (IoT): a **PWA** for managing EV charging. It unifies, under one app, what is today fragmented across each operator's own application, and improves on the Spanish government's REVE app (which only lets you view points and plan a route). It seeds the real Spanish network from the **REVE API** (locations, EVSEs, connectors, tariffs) and adds the functionality REVE lacks: private charging points with paid use, bookings, price/time charging optimisation, charge simulation, and (candidate) AI/agent features. Alongside the app, the thesis includes a brief business plan, a deployment/scaling/profitability strategy, and a roadmap (including the transition to a native mobile app).

**The thesis pillar is the application itself** — its conception, design, full-stack development, deployment, and viability. The charging optimiser and the AI/agent features are *value-add functionalities of the app*, not separate cores standing apart from it.

**Goal:** a real, deployed, usable application to demo at thesis defense, publicly accessible.

---

## Data strategy

| Source | Role | Provides |
| --- | --- | --- |
| **REVE API** | Real-world map layer (seed source) | Spanish CPO catalogue (locations, EVSEs, connectors), tariffs, OCPI 2.2.1 metadata. Seeded once into Postgres; **live availability is not modelled** (no constant status feed) — points show as available by default, illustrative only. |
| **REE / PVPC** | Hourly electricity prices (Spain) | Drives owner dynamic pricing (PVPC + margin) and the smart home-charging optimiser. Public API, no token. |
| **Vehicle catalogue** | Simulation input | Curated table of common EVs in Spain (battery capacity, max AC/DC charging power) seeded from public spec sheets. |
| **User-generated** | Platform contribution | Private charging points with public/private toggle, paid use, bookings, recorded sessions |

REVE provides the real network presence; PVPC provides the economics; user-generated points provide the platform contribution.

> **ACN-Data was dropped (2026-06-21).** Caltech's historical-session dataset was originally to calibrate occupancy/session realism. It stayed internal-only, never landed (blocked on a token, only a smoke test ran), and added nothing user-facing. It now survives only as a documented *road not taken* in the thesis — see [thesis/indice.md](thesis/indice.md). Live availability is **not modelled** — points default to available (illustrative); occupancy appears only for any artificial demo data.

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
- **Live availability is not modelled** — REVE provides no constant status feed, so points show as available by default (illustrative); occupancy appears only for artificial demo data.
- **User-contributed points** stored in `charging_points` alongside REVE-seeded points, distinguished by a `source` column.
- **OCPI 2.2.1-aligned schema** so future commercial CPO agreements plug in by extending the `source` enum.

---

## Features

> Live implementation status for these features (implemented / mock UI / planned): [features.md](features.md).

1. **Map** — REVE + public user points with filters (availability, connector, price), Google Maps redirect
2. **Point detail** — real data from REVE + booking
3. **Pre-charge simulation** — driver picks car model + connector (+ SoC range): predicted duration, energy, cost (spec/physics-based: power = min(vehicle, connector), AC/DC-aware taper)
4. **Smart home charging** — at an owned point: cheapest charging schedule for tonight given PVPC hourly prices and departure time
5. **Private charging points + paid use** — user-registered, private or public; public ones priced as PVPC + margin or fixed; drivers pay from a simulated wallet/ledger, owners credited (real payment processing: stretch)
6. **Driver dashboard** — bookings + recorded session history (energy, duration, cost) + wallet balance/transactions
7. **Owner dashboard** — per-point usage stats (sessions, energy, revenue from the ledger) and management
8. **AI/agent assistant** — *planned (Phase 8); specific features to be decided* — value-add features over the app's own APIs (see [ideas-backlog.md](ideas-backlog.md))

---

## Key screens

| Route | Purpose |
| --- | --- |
| `/` | Dashboard (greeting, summary, nearby points) |
| `/map` | Live map (REVE), centred on the user |
| `/points/:id` | Point detail + pre-charge simulation dialog (booking: planned) |
| `/sessions` | Driver session history |
| `/my-points` | Owner point management + stats (registration wizard: planned) |
| `/profile`, `/login`, … | Profile (opened from the avatar) + auth |

> Implemented vs. placeholder vs. planned, per screen: [features.md](features.md). `/bookings` is planned (Phase 5).

---

## Development phases

Total: **~195–260h** over 12 weeks (~16–22h/week). Each phase has a brief description and acceptance criteria — task plans get written into `phases/phase-N.md` *when starting the phase*, not before.

**Pacing check (2026-06-11):** ~9 weeks to the defense (~mid-August). Remaining work (rest of Phase 2 + Phases 3–7) is ~165–225h, i.e. **19–25h/week** — above the original assumption, with no slack. Mitigations baked in below: thesis chapters written per slice (shrinks the Phase 7 tail), and anything in [Stretch goals](#stretch-goals) only after Phase 6 ships. If anything slips, cut Phase 5 scope — never Phases 4, 6, or 7.

**Revision (2026-06-12):** product refocus — ACN demoted to internal modelling data (Phase 3 shrinks: notebook instead of dashboard), Phase 4 gains the vehicle catalogue + PVPC ingest, Phase 5 regains owner per-point stats and adds session recording. Net scope roughly unchanged; Phases 2–3 are tracking well under their original estimates, which absorbs the additions.

**Revision (2026-06-16):** REVE operational-status mirror dropped. *Operational status* (working/broken) is now assumed always-operational and not modelled; *availability* (free/in use) becomes a `status` column on the EVSE (OCPI value, simulated in Phase 4), and the map's `aggregate_status` is now available/occupied/unknown. A post-seed incremental refresh (`refresh_reve.py`) keeps tariffs fresh under the rate cap. Pricing strategy fixed: serve the real REVE tariff; where none exists, estimate `PVPC + margin` (recommended default AC +0.22 / DC +0.32 €/kWh, owner-overridable). PVPC history backfilled. See [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md).

**Revision (2026-06-21) — scope pivot: the application *is* the thesis.** ACN-Data is dropped entirely (code deleted; kept only as a documented road-not-taken). The thesis core is no longer a novel data combination or a real-session-grounded simulation — it is the **application itself**: a unified, multi-provider EV-charging PWA that improves on REVE, end-to-end built, deployed, and argued viable. The charging optimiser and the (candidate) AI/agent features are value-add functionalities, not separate cores. Concrete changes below: **Phase 3 dropped**; **Phase 4** loses ACN distribution-fitting (occupancy becomes a simple synthetic model) and is reframed as a feature, not "the academic core"; **Phase 5** gains a simulated **wallet/ledger** for paid use; **Phase 6** gains a deployment & scaling strategy; **Phase 7** gains business-plan, deployment and roadmap chapters; **new Phase 8** is a time-gated AI assistant. The thesis outline lives in [thesis/indice.md](thesis/indice.md); deferred ideas in [ideas-backlog.md](ideas-backlog.md).

**Revision (2026-06-28) — redesign shipped; phases renumbered; deploy-early.** Phase 4 is complete (synthetic availability **dropped** — status not modelled; `/api/recommend` moved to Phase 7). The `s-charge` dark redesign + dashboard-first IA shipped as **Phase 5**. The later phases were **renumbered for chronology**: deployment + CI/CD + releases is now **Phase 6 (in progress)**, pulled ahead of the feature work; old Phase 5 (private points/bookings/sessions/wallet, + the optimiser) → **Phase 7**; AI is promoted from a stretch candidate to a committed **Phase 8** (specific features TBD); polish gains a **security review + optimisation** plus the scaling write-up → **Phase 9**; thesis writing → **Phase 10**. Goal: a secure, phone-accessible instance first, then features shipped as tagged releases toward **v1.0.0** = the evaluated build (decision [infra-0001](decisions/infra-0001-deployment.md)). This supersedes the earlier pacing notes' phase numbers.

**Revision (2026-07-27) — Phase 6 open choices closed.** Host confirmed as **Hetzner CX22** (GCP reconsidered and rejected — expired trial, US-only 1 GB free tier, no EU locality); a **registered domain** over a free DuckDNS subdomain (public-suffix friction with Google OAuth authorised domains); **prod images build in CI**; releases are **tagged manually** with the version derived from the tag (`release-please` evaluated and rejected); `main` moves to **PR-required** branch protection. Full plan: [phases/phase-6.md](phases/phase-6.md).

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

Vehicle catalogue, PVPC price ingest, and per-car pre-charge simulation. A **value-add feature** of the app — gives the thesis an evaluable algorithm chapter, but is not the thesis on its own. Two original slices were re-scoped: the synthetic availability model is **dropped** (live status is not modelled — see [Data strategy](#data-strategy)), and the `/api/recommend` optimiser **moves to Phase 7** (it targets an *owned* point, so it needs private points to exist first).

**Done when:**

- [x] `vehicles` table seeded with ~25–30 common Spanish-market EVs (battery kWh, max AC/DC kW)
- [x] PVPC hourly prices ingested daily from REE's public API (cron, same tick pattern as REVE)
- [x] `/api/simulate`: car model + connector (+ SoC range) → predicted duration, energy, cost (REVE tariff or owner price); spec/physics-based (power = min(vehicle, connector), AC/DC taper)
- [x] Simulation UI: the "Simular carga" dialog on point detail; algorithm write-up in [thesis/simulacion-de-recarga.md](thesis/simulacion-de-recarga.md)

Re-scoped: synthetic availability **dropped** (status not modelled); `/api/recommend` **→ Phase 7**; the daily refresh cron is **installed on the server in Phase 6**. Phase 4 is otherwise complete.

### Phase 5 — Frontend redesign + dashboard-first IA — done

Adopted the `s-charge` dark design system (theme tokens, mono-numeric typography, app shell) and restructured the app to a dashboard-first information architecture: bottom nav Inicio · Mapa · Sesiones · Mis puntos, profile via the avatar, map centred on the user. Unbuilt areas (sessions, owner points, stats, reservations) ship as clearly-badged placeholder UI tracked in [features.md](features.md).

**Done when:**

- [x] Dark theme + tokens + mono-numeric type system; all existing screens restyled
- [x] Dashboard-first IA (4-tab nav, profile via avatar); real greeting + nearby points (geolocation + `/api/points?bbox`)
- [x] Sessions / My-points / stats / next-reservation as badged placeholder UI behind `*.mock.ts`
- [x] Lint + build green; merged to `main`

### Phase 6 — Deployment + CI/CD + releases (15–22h) — in progress

Deployment is **pulled forward** (ahead of the remaining feature phases) so there is a secure, phone-accessible HTTPS instance early, with the refresh crons on an always-on server instead of a laptop — then a CI/CD pipeline and semantic-version releases, building toward **`v1.0.0` = the build presented for evaluation**. Architecture + alternatives (Vercel, Supabase, PaaS, …) in [decisions/infra-0001](decisions/infra-0001-deployment.md).

**Done when:**

- [ ] Deployed on a single small VPS behind Caddy (auto-HTTPS), same-origin; reachable at a real HTTPS URL on a phone; PWA installable from production
- [ ] Pre-deploy **security gate** passed (HTTPS+HSTS, host firewall, Postgres not host-published, secrets rotated, OAuth/cookie set for prod origin, CORS locked, backups confirmed)
- [ ] REVE/PVPC refresh crons run on the server (closes Phase 4's open cron item; no longer laptop-dependent)
- [ ] CI/CD: GitHub Actions deploy-on-merge-to-`main`; `main` always deployable; branch protection (PR required + green checks); prod images built in CI so Dockerfile breakage fails before the deploy
- [ ] Semantic-version tagging/releases begin — manual tags, version derived from `git describe` and shown in `/api/health`; `v0.1.0` = first production deploy, `v1.0.0` cut once the evaluated scope is in
- [ ] *(deferred out of the phase)* Map viewport loading — open-on-position + zoom-gated `bbox` fetch + padded cache (small backend `bbox` on `/api/points/map`); no deployment dependency, tracked in [features.md](features.md)

Step-by-step plan, decisions and rationale: [phases/phase-6.md](phases/phase-6.md).

### Phase 7 — Private points, Bookings, Sessions + Wallet + optimiser (30–40h)

Private point CRUD with owner pricing, bookings, session recording, driver history, owner dashboard, a **simulated wallet/ledger** for paid use, and the **`/api/recommend`** smart home-charging optimiser (moved here from Phase 4 — it targets an *owned* point). Replaces the placeholder Sessions/My-points UIs with real data.

**Done when:**

- [ ] Private point creation works end-to-end; public/private toggle controls map visibility
- [ ] Public points priced as PVPC + margin (live) or fixed €/kWh, owner's choice
- [ ] Booking conflict detection rejects overlaps; user can view/cancel bookings
- [ ] Completed bookings and home smart-charges record a session (energy, duration, cost); driver sees real history in `/sessions`
- [ ] Wallet/ledger: per-user balance, top-up (simulated), a paid session debits the driver and credits the owner; both see the transaction history
- [ ] Owner dashboard (`/my-points`): per-point sessions, energy delivered, revenue (from the ledger)
- [ ] `/api/recommend`: owned point + departure + energy needed → cheapest PVPC schedule + 1–2 alternatives; algorithm write-up in [thesis/](thesis/)

### Phase 8 — AI/agent assistant (planned; features to be decided)

A committed value-add layer (no longer a stretch candidate): natural-language / tool-calling features over the app's own APIs (points, simulate, recommend, bookings, prices). **The specific features are not yet decided** — to be picked from the menu in [ideas-backlog.md](ideas-backlog.md) (e.g. NL charging/trip assistant, explain-the-schedule, conversational point search) against remaining time. Keep money/optimisation deterministic; let the LLM orchestrate and explain. Default to the latest capable Claude model.

**Done when:**

- [ ] AI feature set **decided** and recorded (promoted from [ideas-backlog.md](ideas-backlog.md))
- [ ] Implemented over existing APIs as tools; no new data sources
- [ ] Algorithm/architecture write-up for the thesis

### Phase 9 — Polish, security review + optimisation + scaling strategy (22–28h)

Responsive QA, error/empty states, test coverage, a **full security review**, a **performance/optimisation pass**, and the written **deployment & scaling strategy** (the thesis artifact; the live deploy stays single-instance). (Distinct from Phase 6's focused pre-launch security gate — this is the broader audit before the evaluated release.)

**Done when:**

- [ ] All pages tested on a real phone; every API call has loading/error/empty states
- [ ] Backend tests pass with ≥70% coverage on `services/`
- [ ] Security review pass (`/security-review`; auth, secrets, headers, dependencies, rate limits)
- [ ] Performance/optimisation pass (bundle/code-split, query + index review, map payload/viewport)
- [ ] Deployment & scaling strategy written: architecture-for-scale + cost/unit-economics model

### Phase 10 — Thesis writing (45–65h)

Document, diagram, defend. Includes the business and strategy chapters that elevate the work beyond a pure implementation.

**Done when:**

- [ ] Full draft: intro, SoTA, architecture, data, implementation, results, conclusions
- [ ] Architecture + ER diagrams, UI screenshots included
- [ ] Algorithm chapter: formulation, pseudocode, evaluation of the charging optimiser
- [ ] Business plan & viability chapter; deployment/scaling chapter; future-roadmap chapter (incl. native mobile)
- [ ] ≥20 references
- [ ] Defense slides (15–20) + demo plan
- [ ] Tutor approves final version

---

## Stretch goals

Only if hours remain after the evaluated build (`v1.0.0`). Not committed scope; the defense demo must not depend on them.

- **Route optimisation (~10–15h, minimal version).** Given origin/destination, fetch the route polyline from a free routing API (OSRM / OpenRouteService), corridor-query seeded points along it, rank candidate stops by detour + price + Phase 4 predicted session. No consumption modelling, no custom routing engine — those would be 30–40h and are out of scope for this timeline.
- **Real payments.** Replace the simulated wallet/ledger with a real processor (e.g. Stripe test mode) + commission tracking on the owner dashboard.

---

## What makes this thesis-worthy

1. **The application itself** — a real, unified, multi-provider EV-charging PWA that improves on the government REVE app (which only views points and plans routes), built end-to-end: conception, design, full-stack implementation, deployment.
2. **Platform model** — user-contributed charging infrastructure with paid use, bookings and a wallet/ledger economy.
3. **Charging optimiser** — a price/time optimisation algorithm over real PVPC prices, with evaluable output (a value-add feature, written up in the algorithm chapter).
4. **Deployed and usable** — at a real HTTPS URL, installable as a PWA, with at least one real external user.
5. **Business & viability** — a brief business plan, a deployment/scaling/profitability strategy, and a roadmap (incl. native mobile) that argue the product beyond the prototype.
6. **Academically honest** — explicit about what is real vs. not modelled vs. simulated (live availability is not modelled — points show available by default; payments are a simulated ledger), and about the road not taken (ACN-Data).
7. **AI/agent layer** — natural-language/agent features over the app's own APIs as a differentiator (Phase 8; specific features to be decided).
