# EV Charging Point Management App — Final Plan

## Context

Master's thesis (IoT) project: a **PWA** for managing EV charging. Combines the **REVE API** (real Spanish charging network: location, occupation, price) with **ACN-Data** (real historical sessions from Caltech, for analytics/simulation/algorithms). Users can also register their own private charging points.

**Goal:** a real, deployed, usable application to demo at thesis defense, publicly accessible.

---

## Data Strategy

| Source | Role | Provides |
| --- | --- | --- |
| **REVE API** | Real-world map layer | Live CPO locations, status, price, connectors |
| **ACN-Data** | Analytics + simulation backbone | Real historical sessions, charging profiles |
| **User-generated** | Platform contribution | Private charging points with public/private toggle |

REVE provides the real network presence; ACN provides the behavioral data REVE lacks.

---

## Tech Stack

| Layer | Choice |
| --- | --- |
| Frontend | React + TypeScript + Vite, MUI, ECharts, MapLibre GL + react-map-gl, MapTiler tiles (self-hosted Protomaps documented as Phase 6 fallback) |
| PWA | Vite PWA plugin (installable, offline shell) |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| ORM / Migrations | SQLAlchemy 2.0 + Alembic |
| Containers | Docker Compose |
| Deployment | Hetzner VPS (CX22) + Nginx + Let's Encrypt |

**Cost:** ~€65–70/year on Hetzner (VPS ~€4.50/month + domain ~€12/year), or ~€12–180/year on Fly.io + Neon (free tiers cover a thesis demo). Final choice is locked at the start of Phase 6 — see the table there. No Kubernetes, no Vercel, no Supabase.

---

## Architecture

```text
    PWA Frontend (React + Vite)
           │ HTTPS/REST
           ▼
    FastAPI Backend
           │
     ┌─────┼──────────┐
     ▼     ▼          ▼
  PostgreSQL  REVE API    ACN-Data
  (users,     (live,      (bulk imported
   private    cached      once, queried
   points,    ~5 min)     via SQL)
   bookings)
```

- REVE: live-fetched with cache
- ACN: bulk-imported once via ETL
- User-contributed points: stored in PostgreSQL alongside imported data
- Nginx reverse-proxies both frontend and backend from the same VPS

---

## Features

1. **Map** — REVE points with filters (availability, connector, price), Google Maps redirect
2. **Point detail** — real data from REVE + simulated booking
3. **Session analytics** — ACN-powered visualizations (energy, heatmap, utilization, cross-site)
4. **Pre-charge simulation** — predicted duration/energy/cost from ACN distributions
5. **Smart charging algorithm** — recommended start time given constraints
6. **Private charging points** — user-registered, public/private toggle, commission tracking
7. **User dashboard** — sessions, bookings, owned points, cost history
8. **System analytics** (admin) — aggregate stats across the platform

---

## Mocked / Simplified (academically honest)

| Feature | Approach |
| --- | --- |
| Payment | Not implemented |
| Commission payout | Tracked as number only |
| Real-time private point occupation | Derived from bookings |
| REVE write access | Read-only |

---

## Key Screens

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

## Development Phases

Total: **~195–260h** over 12 weeks (~16–22h/week).

### Phase 0 — Tooling Setup (2–4h)

Per-package Claude Code skills and conventions, before any feature work starts. Each package gets its own `CLAUDE.md` so Claude Code loads the right context when editing each side of the stack.

- [ ] Root `CLAUDE.md` written (project orientation, links to PLAN.md, CONTRIBUTING.md, DOCKER.md)
- [ ] `npx autoskills` run from `frontend/` — generated `frontend/CLAUDE.md` reviewed, trimmed of generic filler
- [ ] `backend/CLAUDE.md` hand-written (FastAPI layout, uv commands, Ruff/MyPy, Alembic workflow, Pydantic patterns)
- [ ] Installed skills committed (`.claude/` directory)
- [ ] Commit: `chore: add per-package CLAUDE.md and install frontend skills`

### Phase 1 — Foundation (22–28h) ✅ done

Docker Compose, FastAPI + Postgres + Alembic, auth via `fastapi-users` (email/password + Google OAuth) with Argon2id, **single HttpOnly session cookie** (no refresh token), **email verification + password reset via Resend**, and stdout JSON audit logging. React + MUI scaffold and PWA manifest. Rate limiting deferred to Nginx in Phase 6. Decisions and rationale: [docs/auth-decisions.md](docs/auth-decisions.md). Slice-by-slice plan: [docs/phase-1.md](docs/phase-1.md).

- [x] `docker compose up` starts full stack
- [x] `/docs` and `/api/health` reachable; Alembic migration runs clean
- [x] Email/password auth: register, login (gated on email verification), `/api/users/me`, logout, structured audit logging
- [x] Email verification + password reset emails via Resend
- [x] Google OAuth login works end-to-end via `httpx-oauth`; first-time users auto-provisioned in the `oauth_account` table; existing email accounts can link Google without duplication; OAuth users are verified by default
- [x] PWA installable: Chrome shows "Install app" prompt, iOS Safari "Add to Home Screen" launches standalone
- [x] README documents setup in ≤5 commands (plus linked Google OAuth + Resend setup subsections)

### Phase 2 — REVE + Map (25–30h)

REVE API client with cache, MapLibre GL map (MapTiler tiles), filters, point detail.

- [ ] `/api/points` returns REVE data, cached
- [ ] Map renders real Spanish points, color-coded
- [ ] Filters (availability, connector, price) update markers
- [ ] Detail panel shows operator, price, connectors, address
- [ ] "Navigate" opens Google Maps
- [ ] Usable on mobile viewport

### Phase 3 — ACN Import + Analytics (30–40h)

ETL pipeline, aggregation endpoints, charts dashboard.

- [ ] App-wide structured logging (`app/utils/logging.py` configures root logger to JSON; per-module `logger = logging.getLogger(__name__)` usage) — adopted here because ETL and simulation benefit most from filterable per-module logs
- [ ] ETL imports ACN-Data; row counts match source
- [ ] Core tables populated and indexed
- [ ] Statistics endpoints return aggregations
- [ ] 6+ charts render in <3s
- [ ] Data validation doc (nulls, gaps, ranges) written
- [ ] Slow-query strategy documented

### Phase 4 — Simulation + Algorithm (35–45h)

Distribution fitting, simulation, optimization, session history.

- [ ] Distribution fitting script produces per-station parameters
- [ ] `/api/simulate` returns predicted duration, energy, cost
- [ ] Simulation UI shows predicted session chart
- [ ] `/api/recommend` returns optimal start time + alternatives
- [ ] `/sessions` shows user history with cost breakdown
- [ ] 1–2 page algorithm write-up (reusable in thesis)

### Phase 5 — Private Points + Bookings (25–35h)

Private point CRUD, bookings, public/private toggle, owner dashboard.

- [ ] Private point creation works end-to-end
- [ ] Public/private toggle controls map visibility
- [ ] Booking conflict detection rejects overlaps
- [ ] User can view/cancel bookings
- [ ] Owner dashboard shows bookings, revenue, utilization
- [ ] Commission tracking visible to owner

### Phase 6 — Polish + Deployment (20–25h)

Responsive QA, error states, deploy, tests.

**Deployment target — decide at the start of this phase:**

| Option | Compute | Database | Est. cost | Trade-off |
| --- | --- | --- | --- | --- |
| **A. Hetzner VPS (CX22)** | Self-managed Nginx + Docker Compose | Postgres in the compose stack | ~€65/yr | Full control; more to defend as "infra work"; ~5–10h extra ops (Nginx, TLS renewal, backups cron) |
| **B. Fly.io + Neon** | `fly deploy` per service (`fly.toml` ~20 lines each) | Neon managed Postgres | ~€0–180/yr (free tiers cover a thesis demo) | Less ops time → more hours for Phase 4/7; two vendor dashboards; free-tier idle limits are a defense-day risk to plan for |

Same `Dockerfile` and Alembic migrations either way — the choice only affects the last mile. If switching away from Hetzner, update `docs/auth-decisions.md` (or add an ADR) with a one-paragraph rationale so the paper trail stays clean.

- [ ] All pages tested on real phone
- [ ] Every API call has loading/error/empty states
- [ ] Backend tests pass with ≥70% coverage on `services/`
- [ ] Deployment target chosen (A or B) and rationale recorded in an ADR
- [ ] Deployed at real HTTPS domain
- [ ] SSL auto-renewal verified (Hetzner) / managed certs confirmed (Fly)
- [ ] PWA installable from production on iOS + Android
- [ ] Env vars documented, secrets out of git
- [ ] At least one external user registers + uses the app

### Phase 7 — Thesis Writing (40–60h)

Document, diagram, defend.

- [ ] Full draft: intro, SoTA, architecture, data, implementation, results, conclusions
- [ ] Architecture + ER diagrams, UI screenshots included
- [ ] Algorithm chapter: formulation, pseudocode, evaluation on ACN
- [ ] ≥20 references
- [ ] Defense slides (15–20) + demo plan
- [ ] Tutor approves final version

---

## Risk Watch

| Risk | Mitigation |
| --- | --- |
| Phase 4 slips | Budget buffer; algorithm can start simple (greedy) and iterate |
| Mobile bugs found late | Test on phone during Phase 2, not Phase 6 |
| REVE API limits or changes | Cache aggressively (in-memory TTL); persist last-good snapshot to disk for graceful degradation when REVE 5xx |
| Thesis writing crunch | Start drafting architecture + data chapters in parallel with Phase 3 |

---

## What Makes This Thesis-worthy

1. Two real data sources combined in a novel way (REVE + ACN)
2. Real statistical simulation layer grounded in real sessions
3. Optimization algorithm with evaluable output
4. Platform model (user-contributed infrastructure)
5. Actually deployed at a real URL, installable as PWA
6. Academically honest about what is real vs. simulated
