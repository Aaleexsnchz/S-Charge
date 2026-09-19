# Phase 4 — Frontend redesign + dashboard-first IA

Per [plan.md](../plan.md): adopt the `s-charge` dark design system and restructure the app around a dashboard-first information architecture. Frontend-only — no backend change beyond reusing `GET /api/points?bbox`.

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Design system + restyle | Done | direct to `main` |
| 2 | Dashboard-first IA + real dashboard data | Done | direct to `main` |
| 3 | Placeholder UI for unbuilt areas | Done | direct to `main` |

Shipped as one commit (`feat(frontend): adopt s-charge dark design system and dashboard-first IA`); the slices below describe what it contained.

## Slice 1 — Design system + restyle

**Acceptance:** a single dark theme drives every existing screen; numbers render in a mono font at consistent sizes; no screen still uses the previous light MUI defaults.

- [x] Dark theme tokens (palette, surfaces, radii, elevation) in `theme.ts`
- [x] Mono-numeric type system (Hanken Grotesk for text, JetBrains Mono for figures)
- [x] App shell: top bar with avatar, bottom navigation, safe-area insets
- [x] All existing screens (auth, map, point detail, profile) restyled

## Slice 2 — Dashboard-first IA + real dashboard data

**Acceptance:** `/` is the landing route and shows a real greeting and real nearby points; navigation is four tabs (Inicio · Mapa · Sesiones · Mis puntos) with the profile reachable from the avatar; the map opens centred on the user.

- [x] Router restructured: `/` dashboard, four-tab bottom nav, profile moved behind the avatar
- [x] Greeting + date from `GET /api/users/me`
- [x] Nearby points from browser geolocation (grant-once) + `GET /api/points?bbox`
- [x] Map auto-centres on the user's position on open

## Slice 3 — Placeholder UI for unbuilt areas

**Acceptance:** Sessions, My points, dashboard stats and the next-reservation card render finished-looking UI from `*.mock.ts` fixtures, each visibly badged "datos de ejemplo" so a demo can never be mistaken for real data.

- [x] `sessions.mock.ts`, `myPoints.mock.ts`, `dashboard.mock.ts` fixtures
- [x] "datos de ejemplo" badge on every mock-backed surface
- [x] Each mock surface tracked in [features/](../../features/) so its real phase is known
- [x] Lint + build green
