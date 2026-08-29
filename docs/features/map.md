# Map

**Status:** ✅ Implemented · **Shipped in** [Phase 2](../phases/phase-2.md)

The whole Spanish catalogue on one map, clustered on the GPU, filterable without a round trip, with a point sheet and a Google Maps handoff.

## Today

- **Backend** — `GET /api/points/map` returns the full catalogue as a slim GeoJSON FeatureCollection (~13.7k features, ~3.5 MB of JSON, ~500 KB gzipped).
- **Frontend** — `features/map`: MapLibre GL JS over OpenFreeMap's dark style, native clustering, colour driven by `aggregate_status`. Filter chips (availability, connector, price band) refilter the source client-side. The map centres on the user on open. The service worker serves the FeatureCollection stale-while-revalidate, so a repeat visit paints from cache while the refresh runs behind it.

## Decisions

[fe-0003](../decisions/fe-0003-maplibre-openfreemap.md) — MapLibre + OpenFreeMap, and the load-once model.

## Pending — viewport loading

Rendering at this scale is fine; the cost is the initial download and parse. Planned as one backend + frontend slice in [Phase 14](../plan.md):

- **Open on the user's position** — cache the last known location in `localStorage`, initialise there at city zoom, then refine via `GeolocateControl`. Avoids the Spain-wide flash on open.
- **Zoom-gated viewport fetch** — add an optional `bbox` to `GET /api/points/map` (reusing the `Bbox` handling already in `app/services/points.py`); fetch the current bounds on debounced `moveend`. Below roughly city zoom, do not fetch — that would be the full 13.7k again — and show an "acércate para ver los puntos" hint instead.
- **Padded cache** — request a bbox ~50% larger than the viewport and skip refetching while the view stays inside it; TanStack Query keyed by the snapped bbox caches revisited areas.
- **Low-zoom overview (optional, heavier)** — server-side clustering (PostGIS or vector tiles), only if an all-Spain density view with points is ever actually needed.

### Performance baseline

Lighthouse, production build, mobile preset, 2026-06-13 — recorded here rather than only in the phase that measured it:

| Page | Performance | Accessibility | Best practices | SEO |
| --- | --- | --- | --- | --- |
| `/login` | 94 | 98 | 96 | 82 |
| `/map` | 31 | 100 | 100 | 82 |

After slimming the map payload (772 → 503 KB gzipped, −35%): FCP 3.0 s, LCP 4.5 s, Speed Index 3.4 s on `/map`. The remaining gap is inherent to map pages at this scale — MapLibre's engine, WebGL first paint, a 13.6k-feature source. That is the cost of a first visit; repeat visits now come off the service-worker cache. Remaining lever: fetching the source after first paint.
