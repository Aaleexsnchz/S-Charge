# Phase 2 — REVE seed + Map

Per [PLAN.md](../PLAN.md): REVE seeded into Postgres via cursor-based ETL under the 5 req/hr public-API cap. Frontend renders a map of Spanish charging points with filters and a detail view. Live availability is a static stub from the seed snapshot until Phase 4 wires ACN-driven simulation.

## Slice 1 — REVE seed ETL + mirror schema + `/api/points`

**Acceptance:** with `REVE_API_KEY` set, `python -m scripts.seed_reve` runs unattended via cron, fetches up to ~4 pages per tick under the 5 req/hr cap, idempotently upserts into `cpos`, `charging_points`, `evses`, `connectors`, `tariffs`, and updates a `reve_etl_cursor` row per endpoint. `GET /api/points` returns whatever the cursor has populated so far.

- [x] `reve_etl_cursor` table + Alembic migration seeding one row per endpoint
- [x] Mirror models (`cpos`, `charging_points`, `evses`, `connectors`, `tariffs`) with OCPI 2.2.1 fields + Alembic migration
- [x] REVE async API client with rate-aware request budget
- [x] Idempotent ETL functions (one per endpoint) with `start_page` / `max_pages` and `(rows, last_page, exhausted)` return shape
- [x] Cursor helpers (`read_cursor`, `read_all_cursors`, `record_progress` — folds `mark_completed` via `exhausted=True`, `record_error`)
- [x] `seed_reve.py` orchestrator: per-run budget, priority order, clean exits on `429` / budget exhaustion, `--status` flag
- [ ] `GET /api/points` returning active points with `evses[].connectors[].tariff` joined; optional `bbox`, `connector_standard`, `max_price_per_kwh` query params
- [ ] `GET /api/points/{id}` returning the full nested point shape; 404 matches REVE's `{status_code, status_message}` shape
- [ ] Tests for `/api/points` and `/api/points/{id}` (happy path + filters + 404)

## Slice 2 — Map shell

**Acceptance:** navigating to `/map` lazy-loads a full-viewport map of Spain rendered with vector tiles. Mobile-first layout, safe-area insets. Locate-me control centres on the user's position when granted. The route's JS chunk is split. First Lighthouse audit recorded.

- [ ] Map library + tile source chosen; `fe-NNNN` ADR written at the point of decision
- [ ] Map page lazy-loaded behind `/map`; full-viewport canvas; navigation + locate-me controls; safe-area insets
- [ ] Server-state caching library introduced (`fe-NNNN` ADR if not already chosen)
- [ ] Phase 2 Lighthouse audit recorded; sub-90 scores noted with a deferred-or-fixed line

## Slice 3 — Markers, clustering, point sheet

**Acceptance:** `/map` renders all REVE-seeded points as colour-coded clustered markers, with colour driven by `aggregate_status` (operational / partial / inoperative / unknown). Tapping a marker opens a sheet showing operator, address, connectors with power, tariff, status chip, and two buttons — outlined "Detalles" + contained "Navegar". "Navegar" deep-links to Google Maps directions.

- [ ] Typed `useChargingPoints` hook backed by the server-state lib and the generated API schema
- [ ] GeoJSON source with native clustering and three layers (clusters, cluster counts, unclustered points); colour expression on `aggregate_status`
- [ ] Point sheet component rendering the selected point in Spanish; tap-outside to close
- [ ] "Navegar" opens the universal Google Maps Directions URL (`?api=1&destination=lat,lng`) in a new tab
- [ ] Selecting another marker swaps sheet content without remounting

## Slice 4 — Filters + `/points/:id` + Lighthouse

**Acceptance:** the chip bar at the top of `/map` toggles availability / connector type / price band; unmatched markers vanish (client-side, no extra API calls). "Detalles" navigates to `/points/:id`, a code-split route rendering the full data from `/api/points/{id}`. Phase 2 Lighthouse audit recorded; tested on real iPhone + Android.

- [ ] Filter chip bar with `MapFilters` state lifted to the page; compiled into a map filter expression
- [ ] Filter applied to the unclustered-points layer; empty-state card when zero match
- [ ] `/points/:id` route, lazy-loaded
- [ ] `usePoint(id)` hook via the typed API client
- [ ] Phase 2 Lighthouse audit recorded; mobile testing on real iPhone + Android
