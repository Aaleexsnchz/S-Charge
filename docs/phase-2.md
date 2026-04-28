# Phase 2 — REVE seed + Map

Task breakdown for [PLAN.md](../PLAN.md) Phase 2. Same structure as [phase-1.md](phase-1.md): vertical slices with a single acceptance criterion and cross-domain sub-tasks underneath. Check off tasks as you commit them so progress is visible at a glance.

## Architecture summary

REVE's public API (`https://www.mapareve.es/api/external/v1`) caps at **5 requests per hour** and exposes OCPI 2.2.1-formatted data we have no commercial agreement to redistribute live. Phase 2 therefore treats REVE as a **one-shot seed source**:

- A single ETL run (`scripts/seed_reve.py`) populates `charging_points`, `connectors`, `tariffs`, and `evse_status` from `/locations`, `/cpos`, `/connectors/tariffs`, and `/evses/operational_status` — typically 4–6 REVE calls including pagination.
- An **APScheduler in-process** job refreshes `/connectors/tariffs` once daily at 04:00 Europe/Madrid (≈0.04 calls/hr — well under the 5/hr cap). Locations and CPOs are re-seeded manually as needed.
- The frontend never talks to REVE. It calls `/api/points` (and `/api/points/{id}`), which read from the local Postgres mirror.
- Live availability is **simulated**, not relayed — Phase 2 surfaces the seed-time `accessibility` value as a static stub. Phase 4 replaces it with ACN-derived occupancy distributions.
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

**Acceptance:** with `REVE_API_KEY` set, running `docker compose exec backend uv run python -m scripts.seed_reve` from a fresh DB populates `charging_points`, `connectors`, `tariffs`, and `evse_status` from real REVE data; `GET /api/points` returns those points as JSON; the daily tariff job is registered in the FastAPI lifespan and visible in `/api/health` (or equivalent introspection). The seed is idempotent — re-running upserts without duplicating rows.

**Locked decisions** (rationale captured here so future drift has a paper trail)

- **Scheduler:** `apscheduler` with `AsyncIOScheduler`, started in the FastAPI lifespan. No Celery, no Redis, no host cron, no `pg_cron`. One scheduled job (daily tariff refresh). Library-backed for non-core work; rejected alternatives (Celery+Redis: extra infra; host cron: couples to deploy host; `pg_cron`: extension to maintain) all add operational surface for no benefit at thesis scale.
- **Single `charging_points` table** with a `source` enum (`reve_seed` | `user`) — not separate `reve_locations` / `private_points` tables. Phase 5 user-contributed points reuse the same schema. Connectors and tariffs hang off `charging_points` via FK.
- **Coordinates stored as numeric** (`Numeric(9, 6)` for lat, `Numeric(10, 6)` for lng). REVE returns them as strings — we cast at ingest. Numeric beats float for exactness; geographic operations stay in application code (we don't need PostGIS for Phase 2's simple pin-on-map).
- **OCPI 2.2.1 alignment** — `party_id`, `evse_id`, `connector.standard` (IEC_62196_T2_COMBO etc.), `connector.format` (CABLE/SOCKET), `connector.power_type` (DC/AC_1_PHASE/AC_3_PHASE), `connector.max_electric_power` (watts), `last_updated`. Field names match the OCPI spec verbatim where possible.
- **Idempotent upsert by source ID.** ETL keys on `(source, source_id)` for `charging_points`, where `source_id` is REVE's location UUID. Re-running `seed_reve` updates existing rows, doesn't insert duplicates.
- **Soft-delete on disappearance.** Rows REVE no longer returns get `archived_at` set, not `DELETE`d — keeps historical references valid (e.g., a Phase 5 booking against a now-archived station).
- **API key never logged.** `httpx` client is constructed once with the header, `repr` is overridden if needed, audit events log `source=reve` not the key.

### Task plan

#### Backend

- [ ] **1. `chore(backend): add reve etl and scheduler deps`**
  - Files: `backend/pyproject.toml`, `backend/uv.lock`
  - Deliverable: `apscheduler` declared and locked. (`httpx` is already a transitive dep of `httpx-oauth`; we depend on it directly here.) `uv sync --locked` passes inside the backend container.

- [ ] **2. `feat(backend): charging point models`**
  - Files: `backend/app/models/charging_point.py`, `backend/app/models/__init__.py`
  - Deliverable: SQLAlchemy 2.0 declarative models — `ChargingPoint` (id UUID PK, source enum, source_id text, name, address, city, postal_code, region, country, lat, lng, party_id, cpo_name, time_zone, opening_24_7 bool, last_updated_at, archived_at nullable), `Connector` (FK to charging_point, evse_id, source_id, standard, format, power_type, max_electric_power, max_voltage, max_amperage), `Tariff` (FK to connector, currency, price_per_kwh, type, last_refreshed_at), `EvseStatus` (one row per EVSE, accessibility text, source_updated_at). Source enum: `reve_seed`, `user`.

- [ ] **3. `feat(backend): charging point migration`**
  - Files: `backend/alembic/versions/xxxx_charging_points.py`
  - Deliverable: migration creates the four tables + indexes (`(source, source_id)` unique on charging_points; spatial-ish `(lat, lng)` covering index for bbox queries). `alembic upgrade head` clean on a fresh DB; `alembic downgrade -1` reverts.

- [ ] **4. `feat(backend): reve api client`**
  - Files: `backend/app/integrations/reve.py`, `backend/tests/test_integrations_reve.py`
  - Deliverable: async `RevedClient` wrapping `httpx.AsyncClient` — `x-api-key` header from settings, `base_url` from settings, async `get(path, params=None)` with retry on `429` (exponential backoff capped at one retry — we cannot afford to hammer a 5/hr endpoint), pagination helper `get_paginated(path, params=None) -> AsyncIterator[dict]` consuming `page` / `limit`, and a typed `Pydantic` response wrapper per endpoint. Unit tests stub `httpx` via `pytest_httpx`. The client never logs the key.

- [ ] **5. `feat(backend): reve etl module`**
  - Files: `backend/app/etl/reve.py`, `backend/tests/test_etl_reve.py`
  - Deliverable: four idempotent ingest functions — `import_locations(client, db, *, date_from=None)`, `import_cpos(...)`, `import_tariffs(...)`, `import_evse_status(...)`. Each uses `INSERT ... ON CONFLICT DO UPDATE` (Postgres-native upsert via SQLAlchemy `dialects.postgresql.insert`) keyed on `(source, source_id)`. Coordinates cast from string to `Numeric` at ingest. Rows missing from a full refresh get `archived_at=now()`. Tests cover (a) initial bootstrap from mocked REVE responses, (b) no-op re-run, (c) row removed upstream → `archived_at` set.

- [ ] **6. `feat(backend): seed_reve cli script`**
  - Files: `backend/scripts/seed_reve.py`, `backend/scripts/__init__.py`
  - Deliverable: `python -m scripts.seed_reve` runs all four imports in order with `logging.INFO` per stage, prints REVE-call accounting at the end (e.g., `"REVE calls used: 5/5 (page sizes: locations=100, cpos=20, tariffs=…, status=…)"`). Exits non-zero on any failure. README quickstart updated separately in Slice 4.

- [ ] **7. `feat(backend): apscheduler in fastapi lifespan`**
  - Files: `backend/app/utils/scheduler.py`, `backend/app/main.py`
  - Deliverable: `make_scheduler() -> AsyncIOScheduler` factory; lifespan starts and shuts down the scheduler. A `scheduler_enabled: bool = True` setting (default true, false in tests) gates registration so test runs don't accidentally schedule. The factory is testable in isolation.

- [ ] **8. `feat(backend): daily tariff refresh job`**
  - Files: `backend/app/utils/scheduler.py` (extend), `backend/app/etl/reve.py` (extend if needed), `backend/tests/test_scheduler.py`
  - Deliverable: registered cron trigger — `hour=4, minute=0, timezone="Europe/Madrid"`, `id="reve_tariff_refresh"`. The job opens an `AsyncSession`, reads `tariffs.last_refreshed_at` max as `date_from`, calls `import_tariffs(client, db, date_from=...)`, emits `audit("reve_tariff_refresh_ok", count=...)` or `audit("reve_tariff_refresh_failed", error=...)`. Misfire grace: 1h. No retries on failure (next day picks it up). Test invokes the job directly with a frozen clock and mocked REVE.

- [ ] **9. `feat(backend): /api/points endpoint`**
  - Files: `backend/app/routers/points.py`, `backend/app/schemas/points.py`, `backend/app/main.py` (router include)
  - Deliverable: `GET /api/points` returns the active (non-archived) charging points with their connectors + tariffs joined. Optional query params: `bbox` (`min_lng,min_lat,max_lng,max_lat`), `connector_standard`, `max_price_per_kwh`. Returns a flat array (no pagination for ~100 rows). Pydantic response models live in `schemas/points.py`. Performance budget: <100 ms for the full unfiltered query (indexed on `(source, archived_at)`).

- [ ] **10. `feat(backend): /api/points/{id} endpoint`**
  - Files: `backend/app/routers/points.py` (extend), `backend/app/schemas/points.py` (extend)
  - Deliverable: `GET /api/points/{id}` returns one charging point with full nested data — operator (party_id + cpo_name), connectors with tariffs and live `accessibility`, address, coordinates, opening hours, `last_updated_at`, `last_refreshed_at` (latest tariff refresh). 404 with `status_code/status_message` when not found or archived.

- [ ] **11. `test(backend): /api/points happy + filtered paths`**
  - Files: `backend/tests/test_points.py`
  - Deliverable: tests insert fixture charging points (no real REVE call), exercise the endpoint without filters, with bbox, with connector filter, with price filter, and the 404 case for `/api/points/{id}`.

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

**Acceptance:** `/map` renders all REVE-seeded points as colour-coded clustered markers; tapping a marker opens a 45 %-height MUI bottom sheet showing operator, address, connectors with power, tariff (€/kWh), accessibility chip, and two buttons — outlined "Detalles" and contained "Navegar". "Navegar" deep-links to Google Maps directions. Selecting another marker swaps the sheet content without remounting.

**Locked decisions**

- **GeoJSON source with built-in clustering.** `<Source type="geojson" cluster={true} clusterRadius={40}>` plus three layers (clusters, cluster counts, unclustered points). No third-party clustering library.
- **Marker colour coding from `accessibility`:** `DISPONIBLE` → `#4ADE80` (available green from [screens.md](screens.md)); `NODISPONIBLE` → `#FBBF24` (occupied amber); `RESERVADO` / unknown → `#9AA6B5` (muted). MapLibre paint expression on `circle-color`.
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
  - Deliverable: `MapPage` builds a `FeatureCollection` from the points hook's data (`useMemo` keyed on the array reference), passes it to `<Source id="points" type="geojson" cluster={true} clusterRadius={40}>` with three `<Layer>` children: `clusters` (paint: stepped circle-color + circle-radius by `point_count`), `cluster-count` (symbol with `point_count_abbreviated`), `unclustered-point` (paint: circle-color from accessibility expression). On cluster click, `easeTo` zooms to `getClusterExpansionZoom`. On unclustered click, set selected-point id.

- [ ] **4. `feat(frontend): point bottom sheet`**
  - Files: `frontend/src/components/PointBottomSheet.tsx`
  - Deliverable: MUI `<Drawer anchor="bottom" open={selected !== null} onClose={() => setSelected(null)}>` rendering the selected point per [screens.md §3](screens.md): name (600), operator (secondary), accessibility chip, address row with copy-icon, connector chips (`CCS 150 kW`), large price (`€0.42 / kWh`, 600), button row — outlined "Detalles" + contained "Navegar". Spanish copy throughout (per [frontend-decisions §13](frontend-decisions.md)).

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
- **Filter chips:** `Disponible`, `Type 2`, `CCS`, `CHAdeMO`, `< €0.40/kWh`, `< €0.60/kWh`. "Puntos privados" chip is wired but disabled until Phase 5 (visible as a guide for future work).
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
