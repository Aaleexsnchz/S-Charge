# Feature registry

Living, at-a-glance status of every app feature: what is implemented end-to-end, what is
**mock UI** (front-end only, placeholder data behind a "datos de ejemplo" badge while the
backend is built), and what is planned. This complements [PLAN.md](PLAN.md) — which tracks
phases and acceptance criteria — by giving one cross-feature view. Update a row in the same
change that moves its status.

**Status key:** ✅ Implemented (real data, end-to-end) · 🟡 Mock UI (front-end only, badged
placeholder data) · ⬜ Planned (not built).

| Feature | Status | Backend | Frontend | Notes |
| --- | --- | --- | --- | --- |
| Authentication (email/password, Google, verify/reset) | ✅ | `/api/auth/*`, `/api/users/me` | `features/auth` | ADRs auth-0001..0003 |
| Map of charging points | ✅ | `GET /api/points/map` | `features/map` | GPU clustering; centers on user on open |
| Point detail | ✅ | `GET /api/points/{id}` | `features/points` | |
| Pre-charge simulation | ✅ | `POST /api/simulate` | `features/simulate` | |
| Electricity prices (PVPC) | ✅ | `GET /api/prices/today` | used by simulate | |
| Vehicle catalogue | ✅ | `GET /api/vehicles` | simulate selector | |
| Dashboard — greeting + date | ✅ | `GET /api/users/me` | `features/dashboard` | |
| Dashboard — nearby points | ✅ | `GET /api/points?bbox` | `features/dashboard` | Browser geolocation (grant-once) |
| Dashboard — stats (sessions/kWh/€/CO₂) | 🟡 | — | `dashboard.mock.ts` | No sessions or CO₂ backend |
| Dashboard — next reservation | 🟡 | — | `dashboard.mock.ts` | No reservations backend |
| Sessions history | 🟡 | — | `features/sessions` (`sessions.mock.ts`) | No charging-session model |
| My points (owner) | 🟡 | `ChargingPoint.owner_user_id` exists | `features/my-points` (`myPoints.mock.ts`) | Needs `GET /api/points/mine` |
| Point registration wizard | ⬜ | — | — | "Add" FAB shows "próximamente" |
| Reservations / bookings | ⬜ | — | — | |
| Per-user stats + CO₂ avoided | ⬜ | — | — | No CO₂ calculation anywhere yet |
| Wallet / ledger / payments | ⬜ | — | — | Stretch; see [ideas-backlog.md](ideas-backlog.md) |
| Smart home charging schedule | ⬜ | — | — | PLAN feature 4 (PVPC-aware) |
| AI/agent assistant | ⬜ | — | — | Candidate, time-gated |

## Map performance — viewport loading (deferred)

Today the map fetches **all points once** via `GET /api/points/map` (~13.7k features, ~3.5 MB of
JSON) and clusters them on the GPU. Rendering is fine at that scale; the cost is the initial
download + parse. Planned improvement — its own backend+frontend slice (needs a backend change,
so **not** on the frontend-only redesign branch):

- **Open on the user's position** — cache the last known location in `localStorage`, init the map
  there at city zoom, then refine via `GeolocateControl`. Avoids the Spain-wide flash on open.
- **Zoom-gated viewport fetch** — add an optional `bbox` to `GET /api/points/map` (reuse the
  `Bbox` handling already in `app/services/points.py`); on debounced `moveend`, fetch only the
  current bounds. Below ~city zoom, don't fetch (it would be the full 13.7k again) — show an
  "acércate para ver los puntos" hint instead.
- **Caching** — request a bbox padded ~50 % beyond the viewport and skip refetching while the
  view stays inside it; TanStack Query keyed by the snapped bbox caches revisited areas.
- **Low-zoom overview (optional, heavier)** — server-side clustering (PostGIS / vector tiles)
  only if an all-Spain density view *with points* is ever needed.
