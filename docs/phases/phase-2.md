# Phase 2 — REVE seed + Map

Per [plan.md](../plan.md): REVE seeded into Postgres via cursor-based ETL under the 5 req/hr public-API cap. The frontend renders a map of Spanish charging points with filters and a detail view.

The ETL mirrors three endpoints, not four: operational status (working/broken) is assumed always-operational and not fetched. EVSE *availability* is the `status` column (OCPI value, e.g. `AVAILABLE`) and the map's `aggregate_status` rolls up to available/occupied/unknown; live availability is not modelled ([plan.md](../plan.md) → Data strategy). A post-seed incremental refresh (`refresh_reve.py`) keeps the catalogue fresh under the cap — see [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | REVE seed ETL + mirror schema + `/api/points` | Done | #6 |
| 2 | Map shell | Done | #6 |
| 3 | Markers, clustering, point sheet | Done | #6 |
| 4 | Filters + `/points/:id` + Lighthouse | Done | #6 |

Decisions: [fe-0003](../decisions/fe-0003-maplibre-openfreemap.md) (MapLibre + OpenFreeMap).

## Slice 1 — REVE seed ETL + mirror schema + `/api/points`

**Acceptance:** with `REVE_API_KEY` set, `python -m scripts.seed_reve` runs unattended via cron, fetches up to ~4 pages per tick under the 5 req/hr cap, idempotently upserts into `cpos`, `charging_points`, `evses`, `connectors`, `tariffs`, and updates a `reve_etl_cursor` row per endpoint. `GET /api/points` returns whatever the cursor has populated so far.

- [x] `reve_etl_cursor` table + Alembic migration seeding one row per endpoint
- [x] Mirror models (`cpos`, `charging_points`, `evses`, `connectors`, `tariffs`) with OCPI 2.2.1 fields + Alembic migration
- [x] REVE async API client with rate-aware request budget
- [x] Idempotent ETL functions (one per endpoint) with `start_page` / `max_pages` and `(rows, last_page, exhausted)` return shape
- [x] Cursor helpers (`read_cursor`, `read_all_cursors`, `record_progress` — folds `mark_completed` via `exhausted=True`, `record_error`)
- [x] `seed_reve.py` orchestrator: per-run budget, priority order, clean exits on `429` / budget exhaustion, `--status` flag
- [x] `GET /api/points` returning active points with `evses[].connectors[].tariff` joined; optional `bbox`, `connector_standard`, `max_price_per_kwh` query params
- [x] `GET /api/points/{id}` returning the full nested point shape; 404 matches REVE's `{status_code, status_message}` shape
- [x] Tests for `/api/points` and `/api/points/{id}` (happy path + filters + 404)

## Slice 2 — Map shell

**Acceptance:** navigating to `/map` lazy-loads a full-viewport map of Spain rendered with vector tiles. Mobile-first layout, safe-area insets. Locate-me control centres on the user's position when granted. The route's JS chunk is split. First Lighthouse audit recorded.

- [x] Map library + tile source chosen; `fe-NNNN` ADR written at the point of decision (fe-0003: MapLibre GL JS + OpenFreeMap Positron)
- [x] Map page lazy-loaded behind `/map`; full-viewport canvas; navigation + locate-me controls; safe-area insets
- [x] Server-state caching library introduced (fe-0004: TanStack Query)
- [x] Phase 2 Lighthouse audit recorded; sub-90 scores noted with a deferred-or-fixed line (see "Lighthouse audit" below)

## Slice 3 — Markers, clustering, point sheet

**Acceptance:** `/map` renders all REVE-seeded points as colour-coded clustered markers, with colour driven by `aggregate_status` (operational / partial / inoperative / unknown). Tapping a marker opens a sheet showing operator, address, connectors with power, tariff, status chip, and two buttons — outlined "Detalles" + contained "Navegar". "Navegar" deep-links to Google Maps directions.

- [x] Typed `useChargingPoints` hook backed by the server-state lib and the generated API schema (shipped as `useMapPoints` over `GET /api/points/map`)
- [x] GeoJSON source with native clustering and three layers (clusters, cluster counts, unclustered points); colour expression on `aggregate_status`
- [x] Point sheet component rendering the selected point in Spanish; tap-outside to close
- [x] "Navegar" opens the universal Google Maps Directions URL (`?api=1&destination=lat,lng`) in a new tab
- [x] Selecting another marker swaps sheet content without remounting

## Slice 4 — Filters + `/points/:id` + Lighthouse

**Acceptance:** the chip bar at the top of `/map` toggles availability / connector type / price band; unmatched markers vanish (client-side, no extra API calls). "Detalles" navigates to `/points/:id`, a code-split route rendering the full data from `/api/points/{id}`. Phase 2 Lighthouse audit recorded; tested on real iPhone + Android.

- [x] Filter chip bar with `MapFilters` state lifted to the page; compiled into a map filter expression (shipped as source `setData` refiltering so cluster counts track active filters — see commit message)
- [x] Filter applied client-side, no extra API calls; empty-state card when zero match
- [x] `/points/:id` route, lazy-loaded
- [x] `usePoint(id)` hook via the typed API client
- [x] Mobile testing on real devices via tunnel — map loads and flows well (user-confirmed 2026-06-13). Google OAuth and email links over a tunnel are structurally blocked in local dev (both point at `localhost`); real-device OAuth + email flows get tested on the production domain in [Phase 5](phase-5.md)

## Lighthouse audit (2026-06-13, production build via `pnpm preview`, mobile preset)

| Page | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- |
| `/login` | 94 | 98 | 96 | 82 |
| `/map` | 31 | 100 | 100 | 82 |

Sub-90 lines:

- **SEO 82 (both)** — *fixed*: missing meta description added to `index.html`.
- **`/map` Performance 31** — *partially fixed, rest deferred*: unused `name`/`cpo_name` properties dropped from the map GeoJSON (772 → 503 KB gzipped, −35%). The remaining cost is inherent to map pages under Lighthouse's mobile throttling (MapLibre engine + WebGL first paint + 13.6k-point source); map products routinely score in this range. Further options, carried into the polish phase: service-worker runtime caching of `/api/points/map`, and fetching the source after first paint.
- **Re-audit after the payload fix (2026-06-13):** FCP 3.0 s, LCP 4.5 s, Speed Index 3.4 s on `/map` under mobile throttling — measurably improved; remaining gap accepted as inherent and deferred per the line above.

## Pending

- **Map viewport loading** — the load-once model is unchanged; open-on-position, zoom-gated `bbox` fetch and a padded cache are designed in [features/map.md](../features/map.md) and scheduled for the polish phase.
