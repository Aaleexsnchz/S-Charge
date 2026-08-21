# Session history

**Status:** 🟡 Mock UI · **Real in** [Phase 9](../plan.md)

A record of charges that actually happened: energy, duration, cost, per user and per point.

## Today

- **Backend** — nothing. There is no charging-session model.
- **Frontend** — `features/sessions` renders `sessions.mock.ts`, badged "datos de ejemplo".

## Planned (Phase 9)

A `charging_sessions` table written when a booking completes, `GET /api/sessions` for the driver's own history, `/sessions` on real data with the mock deleted, and the [dashboard](dashboard.md) stat tiles derived from it. Owner-side per-point usage lands here too; revenue waits for the [wallet](wallet.md).

The open question the phase has to answer: **how a booking becomes a session.** There is no hardware and no live status feed, so nothing observes a real charge — either the driver presses start/stop and the app measures wall-clock time, or a completed booking is converted automatically using the [simulation](simulation.md) as the energy figure. Whichever is chosen has to be stated plainly in the thesis.
