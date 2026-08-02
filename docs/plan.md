# EV Charging Point Management App — Plan

The high-level definition of the project: what it is, what it is built from, and the phases it ships in. This document states current scope only — when scope changes, it is rewritten, not annotated. Slice-level detail lives in [phases/](phases/); per-feature status lives in [features/](features/).

## Context

Master's thesis (IoT): a **PWA** for managing EV charging. It unifies, under one app, what is today fragmented across each operator's own application, and improves on the Spanish government's REVE app (which only lets you view points and plan a route). It seeds the real Spanish network from the **REVE API** (locations, EVSEs, connectors, tariffs) and adds the functionality REVE lacks: private charging points with paid use, bookings, price/time charging optimisation, charge simulation, and AI/agent features. Alongside the app, the thesis includes a brief business plan, a deployment/scaling/profitability strategy, and a roadmap (including the transition to a native mobile app).

**The thesis pillar is the application itself** — its conception, design, full-stack development, deployment, and viability. The charging optimiser and the AI/agent features are *value-add functionalities of the app*, not separate cores standing apart from it.

**Goal:** a real, deployed, usable application to demo at thesis defense, publicly accessible.

**Two user roles.** **Drivers** find points on the map, book them, navigate via Google Maps, simulate a charge for their car model before plugging in, charge their own point on an economically optimised schedule, pay for public sessions from a simulated wallet, and review their session history. **Owners** register points for private or public use, price public ones (PVPC + margin, or fixed), and manage/monitor their points' usage and revenue.

---

## Data strategy

| Source | Role | Provides |
| --- | --- | --- |
| **REVE API** | Real-world map layer (seed source) | Spanish CPO catalogue (locations, EVSEs, connectors), tariffs, OCPI 2.2.1 metadata. Seeded once into Postgres, refreshed incrementally. |
| **REE / PVPC** | Hourly electricity prices (Spain) | Drives owner dynamic pricing (PVPC + margin) and the smart home-charging optimiser. Public API, no token. |
| **Vehicle catalogue** | Simulation input | Curated table of common EVs in Spain (battery capacity, max AC/DC charging power) seeded from public spec sheets. |
| **User-generated** | Platform contribution | Private charging points with public/private toggle, paid use, bookings, recorded sessions. |

REVE provides the real network presence; PVPC provides the economics; user-generated points provide the platform contribution.

**Live availability is not modelled.** REVE exposes no constant status feed, so points show as available by default — illustrative, not real-time. The status plumbing (`Evse.status`, the `aggregate_status` rollup, marker colours) exists and would accept a real source later. This is stated plainly in the thesis rather than simulated away.

---

## Tech stack

React + Vite + TypeScript with the TanStack family (Query, Router, Form) and Tailwind + shadcn/ui on the frontend; FastAPI + SQLAlchemy + PostgreSQL on the backend; Docker Compose everywhere; one EU VPS behind Caddy in production. The frontend stack is mid-migration — [tech-stack.md](tech-stack.md) marks what is shipped and what Phase 6 brings, and [thesis/migracion-del-stack.md](thesis/migracion-del-stack.md) argues why.

---

## Architecture

```text
  ┌──────────────────────────────────┐
  │  PWA Frontend (frontend/)        │
  │  React + Vite + Tailwind/shadcn  │
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
  │  users · bookings                │ periodic │  (backend/scripts/)   │
  │  charging_points · connectors    │  writes  │   seed_reve.py        │
  │  tariffs · vehicles · prices     │          │   fetch_pvpc.py       │
  └──────────────────────────────────┘         └───────────────────────┘
```

- **REVE is seeded into Postgres, not proxied.** Its public API caps at 5 requests/hour, which makes a live-mirror architecture impractical. The catalogue is bootstrapped once and owned from then on, refreshed incrementally under the cap.
- **User-contributed points** are stored in `charging_points` alongside REVE-seeded points, distinguished by a `source` column.
- **OCPI 2.2.1-aligned schema** so future commercial CPO agreements plug in by extending the `source` enum.
- **Same origin in production** — Caddy serves the SPA and proxies `/api/*`, so the session stays a first-party HttpOnly cookie with no CORS surface.

---

## Features

1. **Map** — REVE + public user points with filters (availability, connector, price), Google Maps redirect
2. **Point detail** — real data from REVE + booking
3. **Pre-charge simulation** — driver picks car model + connector (+ SoC range): predicted duration, energy, cost (spec/physics-based: power = min(vehicle, connector), AC/DC-aware taper)
4. **Smart home charging** — at an owned point: cheapest charging schedule for tonight given PVPC hourly prices and departure time
5. **Private charging points + paid use** — user-registered, private or public; public ones priced as PVPC + margin or fixed; drivers pay from a simulated wallet/ledger, owners credited (real payment processing: stretch)
6. **Driver dashboard** — bookings + recorded session history (energy, duration, cost) + wallet balance/transactions
7. **Owner dashboard** — per-point usage stats (sessions, energy, revenue from the ledger) and management
8. **AI/agent assistant** — value-add features over the app's own APIs; feature set decided in Phase 11

One document per feature, with live implementation status: [features/](features/).

---

## Key screens

| Route | Purpose |
| --- | --- |
| `/` | Dashboard (greeting, summary, nearby points) |
| `/map` | Map of charging points, centred on the user |
| `/points/:id` | Point detail + pre-charge simulation dialog |
| `/sessions` | Driver session history |
| `/my-points` | Owner point management + stats |
| `/bookings` | Driver bookings (Phase 9) |
| `/profile`, `/login`, … | Profile (opened from the avatar) + auth |

Per-screen implementation status: [features/](features/).

---

## Development phases

Each phase is one meaningful functionality, shipped as a sequence of **slices (one pull request each)** built from **tasks (one commit each)**. A phase's slice plan, open decisions and progress live in its own document under [phases/](phases/) — **written just before the phase starts**, not in advance: a plan worth following needs its decisions raised and settled at the moment there is enough information to settle them. This table is the roll-up.

| # | Phase | Scope | Status | Plan |
| --- | --- | --- | --- | --- |
| 1 | Foundation | Core | Done | [phase-1](phases/phase-1.md) |
| 2 | REVE seed + Map | Core | Done | [phase-2](phases/phase-2.md) |
| 3 | Simulation + algorithm | Core | Done | [phase-3](phases/phase-3.md) |
| 4 | Frontend redesign + dashboard-first IA | Core | Done | [phase-4](phases/phase-4.md) |
| 5 | Deployment + CI/CD + releases | Core | In progress | [phase-5](phases/phase-5.md) |
| 6 | Frontend stack migration | Core | Not started | planned at phase start |
| 7 | Private charging points + owner pricing | Core | Not started | planned at phase start |
| 8 | Smart charging optimiser | Core | Not started | planned at phase start |
| 9 | Bookings + session recording | **Optional** | Not started | planned at phase start |
| 10 | Wallet + paid sessions | **Optional** | Not started | planned at phase start |
| 11 | AI/agent assistant | **Optional** | Not started | planned at phase start |
| 12 | Polish, security + hardening | Core | Not started | planned at phase start |
| 13 | Thesis writing | Core | Not started | planned at phase start |

Releases track this table: a minor version marks a phase shipping, `v0.1.0` is the first production deploy, and **`v1.0.0` is the build presented for the thesis** (see [AGENTS.md](../AGENTS.md) → Releases).

**Optional phases and the cut order.** Phases 9–11 are the ones that come out if the schedule tightens, dropped **from the bottom up: 11 (AI) first, then 10 (wallet), then 9 (bookings + sessions)**. They are optional because none of them is load-bearing for a pillar in [What makes this thesis-worthy](#what-makes-this-thesis-worthy) on its own: the platform model is argued by Phase 7, the algorithm chapter by Phase 8, and the deployment pillar by Phase 5.

Everything marked Core is not negotiable. Cutting a phase means the feature keeps its ⬜ status in [features/](features/) and its mock UI stays badged — the app must never present a cut feature as if it worked.

### Phase 1 — Foundation — done

Docker Compose, FastAPI + Postgres + Alembic, auth via `fastapi-users` (email/password + Google OAuth) with Argon2id, single HttpOnly session cookie, email verification + password reset via Resend, stdout JSON audit logging, plus the React + Vite + MUI frontend scaffold with auth pages and PWA installability.

**Done when:**

- [x] Email/password auth: register, login (gated on verification), `/api/users/me`, logout, audit logging
- [x] Email verification + password reset emails via Resend
- [x] Google OAuth end-to-end via `httpx-oauth`; first-time users auto-provisioned; existing accounts linkable
- [x] Frontend scaffold serves the six auth pages (login, register, check-email, verify-email, forgot-password, reset-password); Spanish copy; PWA installable on iOS Safari and Chrome

### Phase 2 — REVE seed + Map — done

REVE seeded into Postgres via cursor-based ETL under the 5 req/hr public-API cap. The frontend renders a map of Spanish charging points with filters and a detail view.

**Done when:**

- [x] REVE seed runs unattended on a schedule; full-Spain bootstrap completes in ~12 days
- [x] `/api/points` and `/api/points/{id}` serve seeded points
- [x] Map renders with filters (availability, connector, price band), point detail, Google Maps "Navegar" deep link
- [x] Tested on real iPhone + Android

### Phase 3 — Simulation + algorithm — done

Vehicle catalogue, PVPC price ingest, and per-car pre-charge simulation — a value-add feature that also yields the thesis's evaluable algorithm chapter.

**Done when:**

- [x] `vehicles` table seeded with ~25–30 common Spanish-market EVs (battery kWh, max AC/DC kW)
- [x] PVPC hourly prices ingested daily from REE's public API
- [x] `/api/simulate`: car model + connector (+ SoC range) → predicted duration, energy, cost (REVE tariff or owner price); spec/physics-based (power = min(vehicle, connector), AC/DC taper)
- [x] Simulation UI: the "Simular carga" dialog on point detail; algorithm write-up in [thesis/simulacion-de-recarga.md](thesis/simulacion-de-recarga.md)

### Phase 4 — Frontend redesign + dashboard-first IA — done

Adopted the `s-charge` dark design system (theme tokens, mono-numeric typography, app shell) and restructured the app to a dashboard-first information architecture: bottom nav Inicio · Mapa · Sesiones · Mis puntos, profile via the avatar, map centred on the user. Unbuilt areas ship as clearly-badged placeholder UI until their phase lands.

**Done when:**

- [x] Dark theme + tokens + mono-numeric type system; all existing screens restyled
- [x] Dashboard-first IA (4-tab nav, profile via avatar); real greeting + nearby points (geolocation + `/api/points?bbox`)
- [x] Sessions / My-points / stats / next-reservation as badged placeholder UI behind `*.mock.ts`
- [x] Lint + build green; merged to `main`

### Phase 5 — Deployment + CI/CD + releases — in progress

Deployment comes before the remaining feature work so there is a secure, phone-accessible HTTPS instance early, with the refresh ETLs on an always-on server instead of a laptop — then a CI/CD pipeline and semantic-version releases. Architecture and rejected alternatives: [decisions/infra-0001](decisions/infra-0001-deployment.md).

**Done when:**

- [ ] Deployed on a single small VPS behind Caddy (auto-HTTPS), same-origin; reachable at a real HTTPS URL on a phone; PWA installable from production
- [ ] Pre-deploy **security gate** passed (HTTPS+HSTS, host firewall, Postgres not host-published, secrets rotated, OAuth/cookie set for prod origin, CORS locked, backups confirmed)
- [ ] REVE/PVPC refresh ETLs run on the server, not the laptop
- [ ] CI/CD: deploy on merge to `main`; branch protection (PR required + green checks); prod images built in CI so Dockerfile breakage fails before the deploy
- [ ] Version derived from the git tag and shown in `/api/health`; `v0.1.0` tagged at the first production deploy

### Phase 6 — Frontend stack migration — not started

Move the frontend onto one coherent stack before any new screens are built on the old one: **Tailwind v4 + shadcn** replacing MUI and Emotion, **TanStack Router** replacing React Router, and **TanStack Form + Zod** for the forms the app does not yet have. The s-charge dark design system is preserved — it is re-expressed as Tailwind tokens, not redesigned.

Two things justify the timing. Every later phase adds screens (registration wizard, optimiser, bookings, wallet, owner dashboard), so migrating now converts ~10 screens instead of ~18. And dropping Emotion removes runtime CSS-in-JS entirely, which is measurable: the Phase 2 Lighthouse audit scored `/map` at 31, and the before/after belongs in the thesis performance section as a result rather than a claim.

**Runs after the deployment**, not before: the migration consumes almost everything Phase 5 builds — CI building the frontend prod image, the committed API schema, the pre-push gate, and a deployed URL to check each slice on a real phone — while the deployment gains nothing from the migration in return. The ordering argument in full: [phases/phase-5.md](phases/phase-5.md) → Start here. The full argument — why the original MUI decision was right, why it expires, the alternatives weighed (including staying on MUI with Pigment CSS, which MUI documents as early alpha) and how the result gets measured — is the thesis chapter [migracion-del-stack.md](thesis/migracion-del-stack.md), which covers this and the other stack changes.

**Done when:**

- [ ] Lighthouse + bundle size measured **before** the first change, and again at the end
- [ ] Tailwind v4 + shadcn installed; the s-charge tokens (palette, surfaces, radii, mono-numeric type) expressed as Tailwind theme tokens
- [ ] Every screen converted; `@mui/*`, Emotion and notistack removed from `package.json`
- [ ] TanStack Router replaces React Router, with typed params and the auth root loader preserved
- [ ] TanStack Form + Zod in place as the form layer
- [ ] Charts moved off MUI X Charts (nothing renders charts on real data yet, so this is a swap of the placeholder)
- [ ] Re-tested on a real phone at the 360px reference width; no visual regressions against the current build

### Phase 7 — Private charging points + owner pricing — not started

The platform contribution: a user registers their own charging point, chooses whether it is private or publicly listed, and prices it. Replaces the placeholder My-points UI with real data.

**Done when:**

- [ ] Point registration works end-to-end (location, connector type, power, visibility)
- [ ] Public/private toggle controls whether the point appears on the map
- [ ] Public points priced as PVPC + margin (live) or a fixed €/kWh, owner's choice
- [ ] `/my-points` lists, edits and deletes the user's real points (mock removed)

### Phase 8 — Smart charging optimiser — not started

The `/api/recommend` optimiser: at a point the user owns, the cheapest schedule to charge tonight given the PVPC curve and a departure time. It depends only on owned points (Phase 7) and the price history (Phase 3), so it ships as soon as that dependency exists rather than behind the rest of the feature work — it is a thesis pillar and must not be what gets cut.

**Done when:**

- [ ] `/api/recommend`: owned point + departure + energy needed → cheapest PVPC schedule + 1–2 alternatives, with the saving against charging now
- [ ] Optimiser UI at an owned point
- [ ] Algorithm write-up in [thesis/](thesis/): formulation, pseudocode, evaluation

### Phase 9 — Bookings + session recording — not started

Reserving a point and recording what actually happened. Turns the dashboard's next-reservation card and the Sessions screen into real data.

**Done when:**

- [ ] Booking creation with conflict detection that rejects overlaps; user can view and cancel bookings
- [ ] `/bookings` screen; the dashboard's next-reservation card reads real data
- [ ] Completed bookings record a session (energy, duration, cost)
- [ ] `/sessions` shows real history (mock removed); dashboard stats derive from it
- [ ] Owner sees per-point sessions and energy delivered on `/my-points`

### Phase 10 — Wallet + paid sessions — not started

The economics: a simulated wallet/ledger so a session at someone else's public point moves money from driver to owner.

**Done when:**

- [ ] Wallet/ledger: per-user balance, simulated top-up, transaction history
- [ ] A paid session debits the driver and credits the owner; both see the movement
- [ ] Owner dashboard shows revenue derived from the ledger

### Phase 11 — AI/agent assistant — not started

A value-add layer of natural-language / tool-calling features over the app's own APIs (points, simulate, recommend, bookings, prices). Money and optimisation stay deterministic; the LLM orchestrates and explains. The **specific feature set is decided at the start of the phase**, from the menu in [ideas-backlog.md](ideas-backlog.md), against remaining time.

**Done when:**

- [ ] AI feature set decided and recorded in its phase plan
- [ ] Implemented over existing APIs as tools; no new data sources
- [ ] Architecture write-up for the thesis

### Phase 12 — Polish, security + hardening — not started

Responsive QA, error/empty states, test coverage, a full security review and a performance pass. The written deployment & scaling strategy moved to Phase 13 — it is a thesis artifact, not code.

**Done when:**

- [ ] All pages tested on a real phone; every API call has loading/error/empty states
- [ ] Backend tests pass with ≥70% coverage on `services/`
- [ ] Security review pass (auth, secrets, headers, dependencies, rate limits)
- [ ] Performance pass (bundle/code-split, query + index review, map payload/viewport)
- [ ] **Content-Security-Policy in the `Caddyfile`.** HSTS is the only security header today. `HttpOnly` stops JavaScript reading the session cookie but not an XSS payload issuing authenticated requests with it, so CSP is the control that actually limits the blast radius of the threat [thesis/robo-de-sesion.md](thesis/robo-de-sesion.md) analyses — a chapter that currently argues about DBSC and DPoP while the cheap mitigation is absent. **Must come after the Phase 6 migration**: MUI and Emotion inject inline `<style>` tags, forcing `style-src 'unsafe-inline'` and negating most of the benefit; Tailwind compiles to a static stylesheet and makes a strict policy practical
- [ ] **Advisory lock on the REVE ETL tick.** `reve_etl_cursor` is one row per endpoint, read-modify-written every tick, and two concurrent runs corrupt the refresh watermark — the field whose loss produced the July 2026 tariff gap. This is reachable without any scaling: running `refresh_reve` by hand while the hourly cron ticks is two writers. A Postgres advisory lock at the top of `_run_tick`, exiting quietly if another run holds it
- [ ] **Automated backup-restore verification.** The restore is currently exercised by hand, and a backup nobody has restored is a hypothesis. A script that restores the latest dump into a throwaway container and asserts row counts plus `alembic current` at head turns "we take backups" into "we verify they restore" — the stronger claim, and cheap

### Phase 13 — Thesis writing — not started

Document, diagram, defend. Includes the business and strategy chapters that elevate the work beyond a pure implementation.

**Done when:**

- [ ] Full draft: intro, SoTA, architecture, data, implementation, results, conclusions
- [ ] Architecture + ER diagrams, UI screenshots included
- [ ] Algorithm chapter: formulation, pseudocode, evaluation of the charging optimiser
- [ ] Business plan & viability chapter; future-roadmap chapter (incl. native mobile)
- [ ] Deployment & scaling chapter: architecture-for-scale + cost/unit-economics model. **Argued, not built** — the live deploy stays a single VPS. The chapter's job is to name where one box breaks first (concurrent connections, image builds competing with Postgres for RAM, no failover during a deploy) and what replaces each part at each step: managed Postgres, an image registry so the host only pulls, a second node behind a load balancer, and container orchestration (Kubernetes, ECS) only once there is a fleet to schedule. Justifying why orchestration is *not* used at this scale is as much a result as describing when it would be. Source material and the full gap register: [production-readiness.md](production-readiness.md) — the strongest parts are the ones specific to this system rather than generic (the scheduler cannot be replicated under a 5 req/hr cap; the ETL cursor races; in-process rate limiting weakens as replicas multiply), plus the two disciplines a multi-node move forces: **expand/contract migrations** and **observability**, of which there is currently none
- [ ] Compliance section in the business chapter: **GDPR is unaddressed and unrecorded**, in an app storing EU personal data (`users`, `oauth_account`). Name what real users would make binding — privacy policy, lawful basis, processor agreements (Hetzner, Resend, Google), retention, right to erasure, portability, 72-hour breach notification — and note that erasure is not merely a missing endpoint, since deleting a user has to reckon with their sessions, bookings and ledger rows. Arguing the posture is legitimate chapter content even with nothing built; having never considered it is not
- [ ] ≥20 references
- [ ] Defense slides (15–20) + demo plan
- [ ] Tutor approves final version

---

## Stretch goals

Only if hours remain after the evaluated build (`v1.0.0`). Not committed scope; the defense demo must not depend on them. Full list: [ideas-backlog.md](ideas-backlog.md).

- **Route optimisation (minimal version).** Origin/destination → route polyline from a free routing API (OSRM / OpenRouteService) → corridor-query seeded points along it → rank candidate stops by detour + price + predicted session. No consumption modelling, no custom routing engine.
- **Real payments.** Replace the simulated wallet/ledger with a real processor (e.g. Stripe test mode) + commission tracking on the owner dashboard.

---

## What makes this thesis-worthy

1. **The application itself** — a real, unified, multi-provider EV-charging PWA that improves on the government REVE app (which only views points and plans routes), built end-to-end: conception, design, full-stack implementation, deployment.
2. **Platform model** — user-contributed charging infrastructure with paid use, bookings and a wallet/ledger economy.
3. **Charging optimiser** — a price/time optimisation algorithm over real PVPC prices, with evaluable output.
4. **Deployed and usable** — at a real HTTPS URL, installable as a PWA, with at least one real external user.
5. **Business & viability** — a brief business plan, a deployment/scaling/profitability strategy, and a roadmap (incl. native mobile) that argue the product beyond the prototype.
6. **Academically honest** — explicit about what is real, what is not modelled (live availability), and what is simulated (the payment ledger), and about the roads not taken.
7. **AI/agent layer** — natural-language/agent features over the app's own APIs as a differentiator.
