---
id: fe-0003
status: accepted
phase: 2
date: 2026-06
related: [fe-0002]
---

# fe-0003: MapLibre GL JS + OpenFreeMap vector tiles for the map

**Decision.** The `/map` route renders with [MapLibre GL JS](https://maplibre.org/) (the open-source fork of Mapbox GL JS v1) over [OpenFreeMap](https://openfreemap.org/) vector tiles, using the hosted **Dark** style (`/styles/dark`) as the basemap, matching the app's dark design system. Charging points load once from `GET /api/points/map` (a slim GeoJSON FeatureCollection, ~770 KB gzipped for the full Spanish catalogue) into a MapLibre GeoJSON source with native clustering; filters compile to MapLibre filter expressions evaluated client-side.

**Rationale.** Three constraints drive the choice: ~13,600 markers on a mid-range phone, zero budget, and no API-key management for a public thesis repo.

- *MapLibre* renders via WebGL, so 13k points + clustering stay fluid on mobile where DOM-marker approaches degrade. Its GeoJSON sources cluster natively (`cluster: true`), which is exactly the shape the backend map endpoint serves — no client-side clustering library needed. BSD-licensed, no token, actively maintained (Amazon, Meta and others fund it).
- *OpenFreeMap* serves Mapbox-GL-compatible vector tiles with no API key, no registration, no usage caps, financed by donations and run on open data (OpenStreetMap). For a thesis demo this removes both the cost ceiling and the "secret in the frontend bundle" problem entirely. The hosted styles are modern and low-contrast, which keeps colour-coded availability markers legible.
- The map JS (~230 KB gzipped) ships only in the lazy-loaded `/map` chunk, so auth pages and the dashboard don't pay for it.

**Implementation.** `maplibre-gl` as a direct dependency; the OpenFreeMap style URL referenced from the map page. Map controls are dark-styled, attribution compact, marker and cluster colours drawn from the app's status palette, and the map auto-centres on the user on open. Map state (camera, selected point) stays in the page component; server data flows through TanStack Query. Points still load once for the whole country — viewport/`bbox` loading is open work, designed in [features/map.md](../features/map.md).

**Rejected alternatives.**

- *Leaflet + markercluster.* Mature and simpler, but raster tiles and DOM markers: 13k points need plugin clustering and still jank on mobile; no vector styling. The plan's acceptance criteria (vector tiles, GeoJSON cluster layers) were written against the GL model.
- *Mapbox GL JS.* The original, but proprietary since v2: requires an access token, bills past the free tier, and the token would live in the public repo's build. No benefit over MapLibre for this use.
- *Google Maps JS API.* Best-known basemap, but requires a billing-enabled key, and marker rendering at this volume needs their paid vector/WebGL features. The product already deep-links to Google Maps for navigation ("Navegar"), which captures its value without embedding it.
- *MapTiler / Protomaps as tile source.* MapTiler's free tier is polished but needs an account, a key and a 100k-loads/month cap; Protomaps self-hosting adds an extract pipeline and hosting for no demo-visible gain. OpenFreeMap matches the visual bar at zero operational cost.

**References.**

- MapLibre GL JS documentation — clustering example
- OpenFreeMap — hosted styles and usage terms
- [plan/phases/phase-2.md](../plan/phases/phase-2.md) — slice acceptance criteria
