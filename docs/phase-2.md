# Phase 2 — REVE seed + Map

Task breakdown for [PLAN.md](../PLAN.md) Phase 2. Same structure as [phase-1.md](phase-1.md): vertical slices with a single acceptance criterion and cross-domain sub-tasks underneath. Check off tasks as you commit them so progress is visible at a glance.

## Architecture summary

REVE's public API (`https://www.mapareve.es/api/external/v1`) caps at **5 requests per hour** and exposes OCPI 2.2.1-formatted data we have no commercial agreement to redistribute live. Phase 2 therefore treats REVE as a **one-shot seed source**:

- A single ETL run (`scripts/seed_reve.py`) populates `cpos`, `charging_points`, `evses`, `connectors`, and `tariffs` from `/cpos`, `/locations`, `/evses/operational_status`, and `/connectors/tariffs` — typically 4–6 REVE calls including pagination.
- An **APScheduler in-process** job refreshes `/connectors/tariffs` once daily at 04:00 Europe/Madrid (≈0.04 calls/hr — well under the 5/hr cap). Locations and CPOs are re-seeded manually as needed.
- The frontend never talks to REVE. It calls `/api/points` (and `/api/points/{id}`), which read from the local Postgres mirror.
- Live availability is **simulated**, not relayed — Phase 2 surfaces the boolean `is_operational` flag from REVE's `/evses/operational_status` (rolled up per charging point as `aggregate_status`: operational / partial / inoperative / unknown). Phase 4 replaces this binary rollup with ACN-derived occupancy distributions for richer states (charging / reserved / blocked / etc.).
- The schema mirrors OCPI 2.2.1 fields (`party_id`, `evse_id`, IEC 62196 connector standards) so future commercial CPO agreements integrate without schema migration. See [future-work.md](future-work.md) → *Live CPO integration*.

Frontend decisions cited throughout this doc are locked in [frontend-decisions.md](frontend-decisions.md) — MapLibre GL + react-map-gl (§1), MapTiler tiles (§2), TanStack Query introduced here (§11), route-split `/map` chunk (§4).

## Definition of Done (applies to every slice)

- Migration runs clean from a fresh DB (`alembic upgrade head`)
- Backend: `ruff check` + `ruff format --check` + `mypy` pass; new routes covered by at least one test
- Frontend: `tsc -b` + `eslint` pass; manually exercised in the browser at 360 / 768 / 1280 px
- `docker compose up` from a clean clone still works end-to-end (after the operator runs the one-shot seed)
- Committed with Conventional Commits (`feat(backend): …`, `feat(frontend): …`, etc.), one logical change per commit

---

## Slice 1 — REVE seed ETL + mirror schema + `/api/points`

The biggest slice; everything else builds on its DB schema and the typed `/api/points` contract.

**Acceptance:** with `REVE_API_KEY` set, running `docker compose exec backend uv run python -m scripts.seed_reve` from a fresh DB populates `cpos`, `charging_points`, `evses`, `connectors`, and `tariffs` from real REVE data in 4–5 API calls (well within the 5/hr cap); `GET /api/points` returns those points as JSON joined with connectors and tariffs; the daily tariff refresh job is registered in the FastAPI lifespan. The seed is idempotent — re-running upserts without duplicating rows.

**Locked decisions** (rationale captured here so future drift has a paper trail)

- **Scheduler:** `apscheduler` with `AsyncIOScheduler`, started in the FastAPI lifespan. No Celery, no Redis, no host cron, no `pg_cron`. One scheduled job (daily tariff refresh). Library-backed for non-core work; rejected alternatives (Celery+Redis: extra infra; host cron: couples to deploy host; `pg_cron`: extension to maintain) all add operational surface for no benefit at thesis scale.
- **Five tables** mirroring REVE's OCPI 2.2.1 nesting: `cpos`, `charging_points`, `evses`, `connectors`, `tariffs`. EVSE = one physical stall (one car at a time); connectors = sockets on that stall — preserving this distinction matters for Phase 4's per-stall occupancy simulation and for the "future commercial CPO integration plugs into the existing schema" claim in [future-work.md](future-work.md).
- **`charging_points` is dual-source.** A `source` enum (`reve_seed` | `user`) lets Phase 5 user-contributed points share the same table. `cpos.party_id` is FK-linked from `charging_points.party_id` (nullable for `source='user'`). ETL ordering: `cpos` before `locations`.
- **Tariff linkage is per-connector.** `/connectors/tariffs` returns `{evse_id, connector_id, tariffs}` rows — REVE flattens OCPI's `tariff_ids[]` array model. We model this as `connectors.tariff_id` UUID NULL FK → `tariffs.id`.
- **`/locations.evses[].accessibility` is wheelchair accessibility, NOT operational status** (the spec literally says *"Accesible o no, para personas con discapacidad"*). Stored on `evses.wheelchair_accessibility` — useful for a future "solo accesibles" filter; not on the Phase 2 critical path.
- **EVSE operational signal is a boolean** from `/evses/operational_status` — `is_operational` true/false plus `last_operational_status_updated`. The OCPI rich-enum status (`AVAILABLE` / `CHARGING` / `BLOCKED` / `RESERVED` / `OUTOFORDER` / `INOPERATIVE` / `PLANNED` / `REMOVED` / `UNKNOWN`) is only available via `/evses/{evse_id}/status` — a per-EVSE single-fetch endpoint, unaffordable at 600+ EVSEs on a 5/hr budget. Phase 2 surfaces the boolean; Phase 4 layers ACN-derived occupancy on top for the rich state we'd otherwise want.
- **OCPI 2.2.1 alignment** — `party_id`, `evse_id` (e.g. `ES*IOY*E420805`, OCPI-globally-unique), `connector.standard` (IEC_62196_T2_COMBO etc. — stored as text, not enum, since OCPI versions evolve), `connector.format` (CABLE/SOCKET), `connector.power_type` (DC/AC_1_PHASE/AC_3_PHASE), `connector.max_electric_power` (watts). Field names match the OCPI spec verbatim where possible.
- **Coordinates stored as numeric** (`Numeric(9, 6)` for latitude, `Numeric(10, 6)` for longitude). REVE returns them as strings — we cast at ingest. Numeric beats float for exactness; geographic operations stay in application code (we don't need PostGIS for Phase 2's pin-on-map).
- **Tariff display extraction.** REVE simplifies OCPI's `elements[]` and `price_components[]` arrays to single objects. The ingest extracts `price_per_kwh` from `elements.price_components.price` where `type === 'ENERGY'` and `vat_percentage` from `elements.price_components.vat`, casting both string fields to numeric. Full payload preserved in `tariffs.raw_data` JSONB so any downstream display logic (peak/off-peak, restrictions) can fall back to source data without re-querying REVE.
- **Idempotent upsert by `(source, source_id)`** for `charging_points`, by `source_id` (UNIQUE) for `cpos`/`evses`/`connectors`/`tariffs`. Postgres-native upsert via SQLAlchemy `dialects.postgresql.insert(...).on_conflict_do_update(...)`.
- **Soft-delete on disappearance.** Rows REVE no longer returns get `archived_at` set, not `DELETE`d — keeps historical references valid (e.g., a Phase 5 booking against a now-archived station).
- **API key never logged.** `httpx` client constructed once with the header; audit events log `source=reve` and the endpoint path, never the key.

### Schema reference

Column lists below match the REVE OpenAPI spec (Swagger 2.0) verbatim where it specifies a field, with required/nullable annotations from the spec.

`cpos` — `id` UUID PK (ours), `source_id` text NOT NULL, `party_id` text UNIQUE NOT NULL, `cif` text NOT NULL, `name` text NOT NULL, `address` text NOT NULL, `city` text NOT NULL, `city_code` text NOT NULL (INE municipality), `postal_code` text NOT NULL, `region` text NULL (INE province), `state` text NULL (INE autonomous community), `country` text NOT NULL (ISO 3166-1 alpha-2), `phone` text NULL, `website` text NULL, `confirmed_at` timestamp tz NULL (RIPREE registration), `raw_data` JSONB, `source_last_updated_at` timestamp tz NOT NULL, `created_at`, `updated_at`. UNIQUE `(source_id)`, UNIQUE `(party_id)`.

`charging_points` — `id` UUID PK (ours), `source` enum (`reve_seed` | `user`) NOT NULL, `source_id` text NOT NULL, `name` text NULL (spec says not required — fallback render: `"${cpo_name} (${city})"`), `cpo_name` text NULL (denormalised for hot map render), `party_id` text NULL FK→cpos.party_id (NULL for `source='user'`), `version` text NULL (OCPI version per spec — V211/V22/V221), `address` text NOT NULL, `city` text NOT NULL, `postal_code` text NULL, `region` text NULL, `state` text NULL (autonomous community — added per spec), `country_code` text NOT NULL (ISO 3166-1 alpha-2 — keeping alpha-2 only; spec's separate alpha-3 `country` field is dropped as redundant), `latitude` numeric(9,6) NOT NULL, `longitude` numeric(10,6) NOT NULL, `parking_type` text NULL (enum per spec; useful for filters), `facilities` JSONB NULL (array of facility enums per spec), `time_zone` text NOT NULL, `opening_24_7` boolean NOT NULL, `opening_hours` JSONB NULL (regular_hours[] when not 24/7), `charging_when_closed` boolean NULL, `directions` JSONB NULL, `owner_user_id` UUID NULL FK→users (Phase 5), `description` text NULL (Phase 5), `source_last_updated_at` timestamp tz NOT NULL, `archived_at` timestamp tz NULL, `created_at`, `updated_at`. UNIQUE `(source, source_id)`. Indexes on `(archived_at, latitude, longitude)`, `(party_id)`, `(owner_user_id)`.

`evses` — `id` UUID PK (ours), `charging_point_id` UUID FK→charging_points ON DELETE CASCADE NOT NULL, `source_id` text NOT NULL, `evse_id` text NULL (OCPI EVSE_ID — spec says not required; lookup uses our internal `id`), `physical_reference` text NULL, `floor_level` text NULL (added per spec — garage floor), `capabilities` JSONB NULL, `wheelchair_accessibility` text NULL (from `/locations.evses[].accessibility` — disability-access info, NOT operational status), `is_operational` boolean NULL (from `/evses/operational_status.operational_status`), `operational_status_updated_at` timestamp tz NULL, `source_last_updated_at` timestamp tz NOT NULL. UNIQUE `(charging_point_id, source_id)`. Index on `(evse_id)` where not null.

`connectors` — `id` UUID PK (ours), `evse_id` UUID FK→evses ON DELETE CASCADE NOT NULL, `source_id` text NOT NULL, `standard` text NOT NULL (large enum per spec — stored as text since OCPI versions evolve), `format` text NOT NULL (CABLE/SOCKET), `power_type` text NOT NULL, `max_electric_power` integer NULL (watts — spec marks not required), `max_voltage` integer NOT NULL, `max_amperage` integer NOT NULL, `tariff_id` UUID NULL FK→tariffs, `source_last_updated_at` timestamp tz NOT NULL. UNIQUE `(evse_id, source_id)`.

`tariffs` — `id` UUID PK (ours), `source_id` text UNIQUE NOT NULL, `currency` text NOT NULL (ISO 4217), `valid_from` timestamp tz NULL, `valid_to` timestamp tz NULL, `price_per_kwh` numeric(8,4) NULL (extracted from `elements.price_components.price` where `type='ENERGY'`; cast string→numeric at ingest), `price_component_type` text NULL (`ENERGY` / `FLAT` / `PARKING_TIME` / `TIME` — captured for honesty even though we display only ENERGY), `vat_percentage` numeric(5,2) NULL, `step_size` integer NULL, `raw_data` JSONB NOT NULL (full tariff incl. restrictions), `source_last_updated_at` timestamp tz NOT NULL, `last_refreshed_at` timestamp tz NOT NULL.

### Task plan

#### Backend

- [ ] **1. `chore(backend): add reve etl and scheduler deps`**
  - Files: `backend/pyproject.toml`, `backend/uv.lock`
  - Deliverable: `apscheduler` declared and locked. (`httpx` is already a transitive dep of `httpx-oauth`; we depend on it directly here.) `uv sync --locked` passes inside the backend container.

- [ ] **2. `feat(backend): reve mirror models`**
  - Files: `backend/app/models/cpo.py`, `backend/app/models/charging_point.py` (covers `ChargingPoint`, `Evse`, `Connector` per the "one file per aggregate" rule), `backend/app/models/tariff.py`, `backend/app/models/__init__.py`
  - Deliverable: SQLAlchemy 2.0 declarative models for the five tables in [Schema reference](#schema-reference). FK chain: `charging_points.party_id → cpos.party_id`, `evses.charging_point_id → charging_points.id`, `connectors.evse_id → evses.id`, `connectors.tariff_id → tariffs.id`. Relationships eagerly load connectors+tariffs+evses for a single charging-point detail query (`selectinload`); `/api/points` list query joins through `joinedload` on the same chain. Source enum: `reve_seed`, `user`.

- [ ] **3. `feat(backend): reve mirror migration`**
  - Files: `backend/alembic/versions/xxxx_reve_mirror.py`
  - Deliverable: migration creates the five tables + indexes (`UNIQUE (source, source_id)` on charging_points; `UNIQUE party_id` on cpos; `UNIQUE evse_id` on evses; `UNIQUE (evse_id, source_id)` on connectors; `(latitude, longitude)` on charging_points for bbox queries; `(party_id)` on charging_points for CPO joins). Tables created in FK-dependency order: `cpos` → `tariffs` → `charging_points` → `evses` → `connectors`. `alembic upgrade head` clean on a fresh DB; `alembic downgrade -1` reverts cleanly.

- [ ] **4. `feat(backend): reve api client`**
  - Files: `backend/app/integrations/reve.py`, `backend/tests/test_integrations_reve.py`
  - Deliverable: async `ReveClient` wrapping `httpx.AsyncClient` — `x-api-key` header from settings, `base_url` from settings, async `get(path, params=None)` with retry on `429` (exponential backoff capped at one retry — we cannot afford to hammer a 5/hr endpoint), pagination helper `get_paginated(path, params=None) -> AsyncIterator[dict]` consuming `page` / `limit`. Unit tests stub `httpx` via `pytest_httpx`. The client never logs the key.

- [ ] **5. `feat(backend): reve etl module`**
  - Files: `backend/app/etl/reve.py`, `backend/tests/test_etl_reve.py`
  - Deliverable: four idempotent ingest functions, in execution order — `import_cpos(client, db, *, date_from=None)`, `import_locations(client, db, *, date_from=None)` (writes `charging_points` + `evses` + `connectors` atomically per location, capturing `wheelchair_accessibility` from `evse.accessibility`, `parking_type`, `facilities`, `floor_level`), `import_evse_operational_status(client, db, *, date_from=None)` (updates `evses.is_operational` + `operational_status_updated_at` from the boolean `operational_status` field), `import_tariffs(client, db, *, date_from=None)` (upserts `tariffs` and sets `connectors.tariff_id` per `(evse_id, connector_id)` row in the response). Each uses `INSERT ... ON CONFLICT DO UPDATE`. Coordinates cast from string to `Numeric`; tariff `price` and `vat` strings cast to numeric; `Decimal`-typed `restrictions.{min,max}_*` fields preserved in `raw_data` only. Rows missing from a full refresh get `archived_at=now()`. Tests cover (a) initial bootstrap from mocked REVE responses, (b) no-op re-run, (c) row removed upstream → `archived_at` set, (d) tariff linkage written correctly to connectors, (e) `Location.name` null → fallback synthesis at the API layer (not at ingest — we preserve the null).

- [ ] **6. `feat(backend): seed_reve cli script`**
  - Files: `backend/scripts/seed_reve.py`, `backend/scripts/__init__.py`
  - Deliverable: `python -m scripts.seed_reve` runs the four imports in order (cpos → locations → evse_operational_status → tariffs) with `logging.INFO` per stage, prints REVE-call accounting at the end (e.g., `"REVE calls used: 4 (cpos: 1, locations: 1, evse_status: 1, tariffs: 1)"`). Exits non-zero on any failure. README quickstart updated in Slice 4.

- [ ] **7. `feat(backend): apscheduler in fastapi lifespan`**
  - Files: `backend/app/utils/scheduler.py`, `backend/app/main.py`
  - Deliverable: `make_scheduler() -> AsyncIOScheduler` factory; lifespan starts and shuts down the scheduler. A `scheduler_enabled: bool = True` setting (default true, false in tests) gates registration so test runs don't accidentally schedule. The factory is testable in isolation.

- [ ] **8. `feat(backend): daily tariff refresh job`**
  - Files: `backend/app/utils/scheduler.py` (extend), `backend/app/etl/reve.py` (extend if needed), `backend/tests/test_scheduler.py`
  - Deliverable: registered cron trigger — `hour=4, minute=0, timezone="Europe/Madrid"`, `id="reve_tariff_refresh"`. The job opens an `AsyncSession`, reads `MAX(tariffs.last_refreshed_at)` as `date_from`, calls `import_tariffs(client, db, date_from=...)`, emits `audit("reve_tariff_refresh_ok", count=...)` or `audit("reve_tariff_refresh_failed", error=...)`. Misfire grace: 1h. No retries on failure (next day picks it up). Test invokes the job directly with a frozen clock and mocked REVE.

- [ ] **9. `feat(backend): /api/points endpoint`**
  - Files: `backend/app/routers/points.py`, `backend/app/schemas/points.py`, `backend/app/main.py` (router include)
  - Deliverable: `GET /api/points` returns active (non-archived) charging points with `evses[].connectors[].tariff` joined. Optional query params: `bbox` (`min_lng,min_lat,max_lng,max_lat`), `connector_standard` (single value or comma-list), `max_price_per_kwh`. Returns a flat array (no pagination for ~100 rows). Pydantic response models live in `schemas/points.py`. Performance budget: <100 ms for the full unfiltered query (indexed on `(archived_at, latitude, longitude)`).

- [ ] **10. `feat(backend): /api/points/{id} endpoint`**
  - Files: `backend/app/routers/points.py` (extend), `backend/app/schemas/points.py` (extend)
  - Deliverable: `GET /api/points/{id}` returns one charging point with full nested data — `cpo` (party_id + name + cif + address from the `cpos` join), `evses[].connectors[].tariff`, address, coordinates, opening hours, `directions` (from JSONB), `source_last_updated_at`, latest `last_refreshed_at` across the point's tariffs. 404 with `{status_code, status_message}` when not found or archived (matching REVE's own 404 shape so the frontend handles both transparently).

- [ ] **11. `test(backend): /api/points happy + filtered paths`**
  - Files: `backend/tests/test_points.py`
  - Deliverable: tests insert fixture cpos/charging_points/evses/connectors/tariffs (no real REVE call), exercise the endpoint without filters, with bbox, with connector_standard filter, with max_price_per_kwh filter, and the 404 case for `/api/points/{id}`.

#### Docs

- [ ] **12. `docs(backend): document REVE seed pattern in CLAUDE.md`**
  - Files: `backend/CLAUDE.md` — add a small "REVE seed (Phase 2)" section with one-line links to this doc and `app/etl/reve.py` + `app/integrations/reve.py`. Same minimal style as the "Auth (Phase 1)" pointer — file map and acceptance criteria live here, not there.

---

## Slice 2 — Map shell on `/map`

**Acceptance:** navigating to `/map` lazy-loads a full-viewport MapLibre map of Spain rendered with MapTiler dark tiles, on mobile-first layout with safe-area insets. No points yet. Locate-me FAB centres on user position when granted. The route's JS chunk is split (verified in `dist/stats.html`). First Lighthouse audit run — score noted, no fix expected to be needed at this stage.

**Locked decisions**

- **MapLibre GL + `react-map-gl`** per [frontend-decisions §1](frontend-decisions.md). PMTiles protocol handler is **not** registered (we use MapTiler-hosted tiles, no self-hosted PMTiles in Phase 2).
- **MapTiler `streets-v2-dark` style** per §2; `VITE_MAPTILER_KEY` referrer-locked to `http://localhost:5173` and (later) the production origin in the MapTiler dashboard.
- **TanStack Query introduced here** per §11. `<QueryClientProvider>` wraps the router in `main.tsx`, inside `<ThemeProvider>` and outside `<SnackbarProvider>`.
- **Route-level code splitting** per §4 — `lazy: () => import('./pages/MapPage')` in `router.tsx`. Map dependencies (~200 KB gzip) only load on `/map`.
- **Initial view:** centre `[-3.7038, 40.4168]` (Madrid), zoom `5.5` (covers peninsular Spain + Balearics). Min zoom `5`, max zoom `18`.
- **No imperative ref dance.** The map is a declarative `<Map>` with `<NavigationControl>`, `<GeolocateControl>` from `react-map-gl/maplibre`. State (camera, selected point) lives in React, not in MapLibre instance refs.

### Task plan

#### Frontend

- [ ] **1. `chore(frontend): add map + query deps`**
  - Files: `frontend/package.json`, `frontend/pnpm-lock.yaml`
  - Deliverable: `maplibre-gl`, `react-map-gl`, `@tanstack/react-query`. Optional: `@tanstack/react-query-devtools` as a dev dep. `pnpm install` clean.

- [ ] **2. `feat(frontend): maptiler env var + key check`**
  - Files: `frontend/.env`, `frontend/.env.example`
  - Deliverable: `VITE_MAPTILER_KEY=` placeholder in `.env.example`; `frontend/.env` gets the actual key. README "Quick start" section gains a one-line "MapTiler key setup" step in Slice 4 docs.

- [ ] **3. `feat(frontend): query client provider`**
  - Files: `frontend/src/main.tsx`, `frontend/src/api/queryClient.ts`
  - Deliverable: a single `QueryClient` exported from `api/queryClient.ts` with default `staleTime: 30_000`, `retry: 1`, `refetchOnWindowFocus: false`. `<QueryClientProvider client={queryClient}>` wraps `<RouterProvider>` in `main.tsx` inside `<ThemeProvider>` and outside `<SnackbarProvider>`.

- [ ] **4. `feat(frontend): map page skeleton`**
  - Files: `frontend/src/pages/MapPage.tsx`, `frontend/src/styles/map.css` (if needed)
  - Deliverable: full-viewport `<Map mapLib={maplibregl} ...>` with the MapTiler dark style URL, initial Spain view, `<NavigationControl position="top-right">`, `<GeolocateControl position="bottom-right">` (the locate-me FAB). Mobile safe-area insets via `env(safe-area-inset-bottom)` on the bottom-right control padding. Renders inside the existing protected `RootLayout` (so the bottom-nav / topbar stay visible).

- [ ] **5. `feat(frontend): lazy /map route`**
  - Files: `frontend/src/router.tsx`
  - Deliverable: `/map` added under the `<ProtectedRoute>` branch with `lazy: () => import('./pages/MapPage')` returning the page as a `Component` named export. Route-level fallback element (small MUI spinner) while the chunk loads.

- [ ] **6. Manual verification**
  - `pnpm build` produces a separate `MapPage-*.js` chunk (visible in `dist/stats.html`). `/map` cold-loads in <1.5 s on throttled fast 3G in Chrome DevTools. Visible map of Spain on a real iPhone in Safari.

---

## Slice 3 — Markers, clustering, bottom sheet

**Acceptance:** `/map` renders all REVE-seeded points as colour-coded clustered markers (colour from `aggregate_status`); tapping a marker opens a 45 %-height MUI bottom sheet showing operator, address, connectors with power, tariff (€/kWh), an operational-status chip, and two buttons — outlined "Detalles" and contained "Navegar". "Navegar" deep-links to Google Maps directions. Selecting another marker swaps the sheet content without remounting.

**Locked decisions**

- **GeoJSON source with built-in clustering.** `<Source type="geojson" cluster={true} clusterRadius={40}>` plus three layers (clusters, cluster counts, unclustered points). No third-party clustering library.
- **Marker colour coding from per-charging-point operational rollup.** Computed at API time as the `aggregate_status` field on each charging point: all EVSEs `is_operational=true` → `operational` (`#4ADE80` available green per [screens.md](screens.md)); some true, some false → `partial` (`#FBBF24` amber); all false → `inoperative` (`#EF4444` red); all unknown → `unknown` (`#9AA6B5` muted). MapLibre paint expression on `circle-color` keys off this string. *Note: this is a binary-rollup signal, not an OCPI rich-enum signal — `is_operational` from `/evses/operational_status` is a boolean per spec. The richer "available vs charging vs reserved" colouring lands in Phase 4 via ACN-derived simulation.*
- **Bottom sheet via MUI `<Drawer anchor="bottom">`** with `PaperProps={{ sx: { borderTopLeftRadius: 16, borderTopRightRadius: 16, height: '45vh' } }}`. Drag-to-dismiss is post-Phase-2 polish; tap-outside-to-close is enough for now.
- **Selected-point state lives in `MapPage`**, not in URL. URL deep-linking to a specific point comes via Slice 4's `/points/:id` route. (This avoids fighting React Router with map-state-as-search-params.)
- **Navegar URL:** `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}` — the universal Google Maps Directions URL. Works on iOS, Android, and desktop. No platform-specific `geo:` URI fallback (extra complexity for marginal UX gain).

### Task plan

#### Frontend

- [ ] **1. `feat(frontend): regenerate openapi schema`**
  - Files: `frontend/src/api/schema.d.ts`
  - Deliverable: `pnpm gen:api` after Slice 1 lands. Type for `paths['/api/points']['get']['responses']['200']['content']['application/json']` is an array of charging-point objects. Commit the generated file.

- [ ] **2. `feat(frontend): useChargingPoints hook`**
  - Files: `frontend/src/api/points.ts`, `frontend/src/api/types.ts` (extend)
  - Deliverable: `useChargingPoints(filters?: PointFilters)` calling `apiClient.GET('/api/points', { params: { query: filters } })` via TanStack Query. Query key `['points', filters]`. Returns `{ data, isPending, error }`. `PointFilters` is a typed re-export from the generated schema.

- [ ] **3. `feat(frontend): geojson source + clustered marker layers`**
  - Files: `frontend/src/pages/MapPage.tsx` (extend), `frontend/src/map/layers.ts`
  - Deliverable: `MapPage` builds a `FeatureCollection` from the points hook's data (`useMemo` keyed on the array reference), passes it to `<Source id="points" type="geojson" cluster={true} clusterRadius={40}>` with three `<Layer>` children: `clusters` (paint: stepped circle-color + circle-radius by `point_count`), `cluster-count` (symbol with `point_count_abbreviated`), `unclustered-point` (paint: `circle-color` from a MapLibre `match` expression on the feature's `aggregate_status` property — `operational`/`partial`/`inoperative`/`unknown`). On cluster click, `easeTo` zooms to `getClusterExpansionZoom`. On unclustered click, set selected-point id.

- [ ] **4. `feat(frontend): point bottom sheet`**
  - Files: `frontend/src/components/PointBottomSheet.tsx`
  - Deliverable: MUI `<Drawer anchor="bottom" open={selected !== null} onClose={() => setSelected(null)}>` rendering the selected point per [screens.md §3](screens.md): name (or fallback `${cpo_name} (${city})` when REVE returned no name), operator (secondary), operational-status chip ("Operativo" / "Parcial" / "No operativo" / "Desconocido" — Spanish copy keyed off `aggregate_status`), address row with copy-icon, connector chips (`CCS 150 kW`), large price (`€0.42 / kWh`, 600), button row — outlined "Detalles" + contained "Navegar". Spanish copy throughout (per [frontend-decisions §13](frontend-decisions.md)).

- [ ] **5. `feat(frontend): navegar deep-link`**
  - Files: `frontend/src/components/PointBottomSheet.tsx` (extend)
  - Deliverable: clicking "Navegar" calls `window.open('https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(`${lat},${lng}`), '_blank', 'noopener')`. No router navigation; opens in new tab/external app on mobile.

- [ ] **6. `feat(frontend): map page wires hook + selection`**
  - Files: `frontend/src/pages/MapPage.tsx` (extend)
  - Deliverable: `MapPage` consumes `useChargingPoints()`, renders `<PointBottomSheet>` outside the `<Map>` so MapLibre doesn't repaint when the sheet opens. Loading state: 2 px accent progress bar at top of the map area. Error state: top toast via notistack (`enqueueSnackbar('No se pudieron cargar las estaciones', { variant: 'error' })`).

---

## Slice 4 — Filters + `/points/:id` + Lighthouse audit

**Acceptance:** the floating filter chip bar at the top of `/map` toggles availability / connector type / price band, and unmatched markers vanish (client-side, no extra API calls). "Detalles" in the bottom sheet navigates to `/points/:id`, which is a code-split detail page rendering the full data shape from `/api/points/{id}`. A Phase 2 Lighthouse audit (Performance / Accessibility / Best Practices / PWA / SEO) runs from Chrome DevTools, scores transcribed to `docs/lighthouse-YYYY-MM-DD.md`, any score under 90 noted with a deferred-or-fixed line.

**Locked decisions**

- **Client-side filtering via MapLibre filter expressions** on the `unclustered-point` layer. We already fetch all points; re-querying the API on filter change wastes round-trips and breaks clustering. The chip bar mutates a `useState` filter object that compiles to a MapLibre `filter: ['all', ...]` expression each render.
- **Filter chips:** `Operativos` (filters by `aggregate_status='operational'`), `Type 2`, `CCS`, `CHAdeMO`, `< €0.40/kWh`, `< €0.60/kWh`. "Puntos privados" chip is wired but disabled until Phase 5 (visible as a guide for future work). The label `Operativos` reflects the boolean signal we actually have — not the OCPI rich-enum "Disponible/Ocupado/Reservado" trio that requires per-EVSE polling.
- **`/points/:id` is its own lazy route**, separate chunk from `/map`. Not a modal. Reasons: shareable URL, browser-back works naturally, doesn't fight the bottom sheet's mount/unmount.
- **Lighthouse cadence:** Phase 2 baseline now, Phase 6 final. Audit recorded in `docs/lighthouse-YYYY-MM-DD.md` per [frontend-decisions §5](frontend-decisions.md). No CI integration.

### Task plan

#### Frontend

- [ ] **1. `feat(frontend): filter chip bar`**
  - Files: `frontend/src/components/MapFilterBar.tsx`, `frontend/src/map/filters.ts`
  - Deliverable: floating horizontal scroll of MUI `<Chip>` toggles at the top of the map (safe-area inset). Active chip: accent fill + canvas text. State lifted to `MapPage` as `MapFilters`. `compileFilter(filters): maplibregl.FilterSpecification` translates state to a MapLibre filter expression; unit-tested in `frontend/src/map/filters.test.ts`.

- [ ] **2. `feat(frontend): apply filter to map layer`**
  - Files: `frontend/src/pages/MapPage.tsx` (extend)
  - Deliverable: `<Layer id="unclustered-point" filter={compileFilter(filters)} ... />`. Cluster recomputation is automatic — MapLibre's clustering operates on the source, not the layer, so we don't need to re-source on filter changes. Empty-result state: when zero points match, show a centred `<Card>` per [screens.md §3](screens.md).

- [ ] **3. `feat(frontend): point detail page`**
  - Files: `frontend/src/pages/PointDetailPage.tsx`
  - Deliverable: page structured per [screens.md §4](screens.md) — hero map snippet (small static `<Map>` centred on the point, `interactive={false}`), header (name + operator + status chip), address row, connectors card (rows with icon + type + power + availability dot), price card, availability card (Phase 2 stub: a placeholder with a "Datos en tiempo real disponibles en la fase 4" note — honest about the simulation gap). Sticky bottom bar with "Reservar" (disabled, Phase 5).

- [ ] **4. `feat(frontend): /points/:id route`**
  - Files: `frontend/src/router.tsx`, `frontend/src/api/points.ts` (extend)
  - Deliverable: `/points/:id` added with `lazy: () => import('./pages/PointDetailPage')`. `usePoint(id)` hook calls `apiClient.GET('/api/points/{id}', { params: { path: { id } } })` via TanStack Query. Bottom-sheet "Detalles" button uses `useNavigate()` to push `/points/${selected.id}`.

#### Docs + verification

- [ ] **5. `docs(frontend): MapTiler + REVE seed quickstart in README`**
  - Files: `README.md` — add a "Map setup (Phase 2)" subsection covering: get a MapTiler API key (free tier, lock to localhost:5173), paste into `frontend/.env`, run `docker compose exec backend uv run python -m scripts.seed_reve` once with `REVE_API_KEY` filled. Expected output line count + REVE-call accounting.

- [ ] **6. `docs: phase 2 lighthouse audit`**
  - Files: `docs/lighthouse-YYYY-MM-DD.md`
  - Deliverable: Chrome DevTools audit on `/map` (the heaviest route) and `/` (the dashboard shell), throttled `Mobile`. Five-score table, plus one paragraph noting any sub-90 score and whether it's deferred or fixed in this slice.

- [ ] **7. `docs: backfill phase-2 task checkboxes; update PLAN.md status`**
  - Files: `docs/phase-2.md` (this doc), `PLAN.md` (status / Phase 2 acceptance)
  - Deliverable: tick every checkbox in this doc that landed; mark Phase 2 as `✅ done` in PLAN.md and the README status table.

---

## Suggested order

1. **Slice 1 first** — backbone. Everything else reads from `/api/points`.
2. **Slice 2** — the map shell renders with the data layer absent, so it's an honest checkpoint that route-splitting + TanStack Query + MapTiler all work before we put markers on top.
3. **Slice 3** — markers and the bottom sheet. Most visible single piece of Phase 2.
4. **Slice 4 last** — filters and the detail page benefit from real points being on the map already; Lighthouse + mobile testing wraps the phase.

Mobile testing is **not** deferred to Phase 6 (per [PLAN.md](../PLAN.md) Risk Watch — *Mobile bugs found late*). Test each slice on a real iPhone + Android device when its frontend tasks land — `ngrok` or Tailscale Funnel against the local Vite dev server is enough.
