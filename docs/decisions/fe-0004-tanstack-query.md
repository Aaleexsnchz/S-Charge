---
id: fe-0004
status: accepted
phase: Phase 2 / Slice 2
date: 2026-06
related: [fe-0003]
---

# fe-0004: TanStack Query for server state

> Append revisions below with date and reason rather than editing in place.

**Decision.** Server state (everything fetched from `/api/*` except the auth bootstrap) is managed with [TanStack Query](https://tanstack.com/query) v5. Queries wrap the existing typed `openapi-fetch` client in small hooks (`useMapPoints`, `usePoint(id)`, …) colocated with the feature that owns them. The React Router root loader keeps owning the initial `/api/users/me` call; auth actions keep using the client directly.

**Rationale.** Phases 2–5 multiply the number of read endpoints (map, point detail, analytics aggregations, simulation results, bookings) and add mutations with invalidation semantics (create booking → refresh bookings + availability). TanStack Query provides the cache, request deduplication, stale-while-revalidate refetching, retry policy and consistent `isPending / isError` states once, instead of re-implementing them per page with `useEffect`. The 13k-point map payload in particular should be fetched once and shared across `/map` visits within a session — exactly its cache model (`staleTime`). It is the de-facto standard (devtools, docs, hiring signal for the thesis writeup) and pairs cleanly with `openapi-fetch`'s typed responses.

**Implementation.** Phase 2 / Slice 2. One `QueryClient` configured in `main.tsx` with conservative defaults (`staleTime` 5 min for catalogue data, no refetch-on-focus for the map source). Feature hooks live next to their feature (`src/map/useMapPoints.ts`, …). Mutations arrive with Phase 5 bookings.

**Rejected alternatives.**

- *SWR.* Lighter, good for plain GETs, but mutations + invalidation (Phase 5) and devtools are weaker; no benefit large enough to deviate from the standard.
- *React Router loaders for everything.* Already in use for auth bootstrap and fine there, but loaders alone don't give caching, deduping or background refresh — every navigation refetches. Hand-rolling that on top means maintaining our own query library.
- *Redux Toolkit Query / Zustand + fetch.* RTK Query drags in Redux for an app with no client-state problem; Zustand is client-state, not server-state, and would still need the cache layer written by hand.

**References.**

- TanStack Query v5 documentation
- [fe-0003](fe-0003-maplibre-openfreemap.md) — the map source this first serves
