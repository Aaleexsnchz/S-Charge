---
id: fe-0003
status: accepted
phase: Phase 2 / Slice 2
date: 2026-06
related: [fe-0002]
---

# fe-0003: MapLibre GL JS + OpenFreeMap vector tiles for the map

> Append revisions below with date and reason rather than editing in place.

**Revisions.**

- *2026-06 (b).* Basemap style switched from **Positron** to OpenFreeMap's **Dark** style (`/styles/dark`) as part of the dark-mode app redesign; map controls are dark-styled and attribution is compact. Marker/cluster colours moved to the app's status palette, and the map now auto-centres on the user on open. The load-once GeoJSON model is unchanged; viewport/`bbox` loading remains future work (see [../features.md](../features.md)).

**Decision.** The `/map` route renders with [MapLibre GL JS](https://maplibre.org/) (the open-source fork of Mapbox GL JS v1) over [OpenFreeMap](https://openfreemap.org/) vector tiles, using the hosted **Positron** style as the basemap. Charging points load once from `GET /api/points/map` (a slim GeoJSON FeatureCollection, ~770 KB gzipped for the full Spanish catalogue) into a MapLibre GeoJSON source with native clustering; filters compile to MapLibre filter expressions evaluated client-side.

**Rationale.** Three constraints drive the choice: ~13,600 markers on a mid-range phone, zero budget, and no API-key management for a public thesis repo.

- *MapLibre* renders via WebGL, so 13k points + clustering stay fluid on mobile where DOM-marker approaches degrade. Its GeoJSON sources cluster natively (`cluster: true`), which is exactly the shape the backend map endpoint serves — no client-side clustering library needed. BSD-licensed, no token, actively maintained (Amazon, Meta and others fund it).
- *OpenFreeMap* serves Mapbox-GL-compatible vector tiles with no API key, no registration, no usage caps, financed by donations and run on open data (OpenStreetMap). For a thesis demo this removes both the cost ceiling and the "secret in the frontend bundle" problem entirely. The Positron style is a modern, low-contrast basemap that keeps colour-coded availability markers legible.
- The map JS (~230 KB gzipped) ships only in the lazy-loaded `/map` chunk, so auth pages and the dashboard don't pay for it.

**Implementation.** Phase 2 / Slices 2–4. `maplibre-gl` added as a direct dependency; style URL `https://tiles.openfreemap.org/styles/positron` referenced from the map page. Map state (camera, selected point) stays in the page component; server data flows through TanStack Query ([fe-0004](fe-0004-tanstack-query.md)).

**Rejected alternatives.**

- *Leaflet + markercluster.* Mature and simpler, but raster tiles and DOM markers: 13k points need plugin clustering and still jank on mobile; no vector styling. The plan's acceptance criteria (vector tiles, GeoJSON cluster layers) were written against the GL model.
- *Mapbox GL JS.* The original, but proprietary since v2: requires an access token, bills past the free tier, and the token would live in the public repo's build. No benefit over MapLibre for this use.
- *Google Maps JS API.* Best-known basemap, but requires a billing-enabled key, and marker rendering at this volume needs their paid vector/WebGL features. The product already deep-links to Google Maps for navigation ("Navegar"), which captures its value without embedding it.
- *MapTiler / Protomaps as tile source.* MapTiler's free tier is polished but needs an account, a key and a 100k-loads/month cap; Protomaps self-hosting adds an extract pipeline and hosting for no demo-visible gain. OpenFreeMap matches the visual bar at zero operational cost.

**References.**

- MapLibre GL JS documentation — clustering example
- OpenFreeMap — hosted styles and usage terms
- [phases/phase-2.md](../phases/phase-2.md) — slice acceptance criteria
