# Dashboard

**Status:** 🟡 Partly mock · **Shipped in** [Phase 4](../phases/phase-4.md)

The landing screen at `/`: who you are, what is near you, and a summary of your activity.

## Today

- ✅ **Greeting + date** from `GET /api/users/me`.
- ✅ **Nearby points** from browser geolocation (grant-once) + `GET /api/points?bbox`.
- 🟡 **Stat tiles** (sessions, kWh, €, CO₂) — `dashboard.mock.ts`, badged "datos de ejemplo". Needs [session history](sessions.md) to be real; CO₂ needs a defensible emissions factor or it should be dropped from the UI.
- 🟡 **Next reservation card** — `dashboard.mock.ts`. Needs [bookings](bookings.md).

Both mock surfaces become real in [Phase 9](../plan.md).
