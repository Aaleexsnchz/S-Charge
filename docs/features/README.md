# Features

One document per feature: what it does, what exists today, and what is still missing. These are living docs — a feature's document is updated in the same change that moves its status, and states current reality only.

**Status key:** ✅ Implemented (real data, end-to-end) · 🟡 Mock UI (front-end only, badged "datos de ejemplo") · ⬜ Planned (not built).

| Feature | Status | Phase | Surfaces |
| --- | --- | --- | --- |
| [Authentication](auth.md) | ✅ | [1](../phases/phase-1.md) | `/login`, `/register`, `/profile` |
| [Charging point catalogue](points.md) | ✅ | [2](../phases/phase-2.md) | `/points/:id` |
| [Map](map.md) | ✅ | [2](../phases/phase-2.md) | `/map` |
| [Vehicle catalogue](vehicles.md) | ✅ | [3](../phases/phase-3.md) | simulation picker |
| [Electricity prices (PVPC)](prices.md) | ✅ | [3](../phases/phase-3.md) | simulation, optimiser |
| [Pre-charge simulation](simulation.md) | ✅ | [3](../phases/phase-3.md) | dialog on `/points/:id` |
| [Dashboard](dashboard.md) | 🟡 | 9 | `/` |
| [Owner points](owner-points.md) | 🟡 | 7 | `/my-points` |
| [Smart home charging](smart-charging.md) | ⬜ | 8 | owned point |
| [Bookings](bookings.md) | ⬜ | 9 | `/bookings` |
| [Session history](sessions.md) | 🟡 | 9 | `/sessions` |
| [Wallet](wallet.md) | ⬜ | 10 | profile / sessions |
| [AI assistant](ai-assistant.md) | ⬜ | 11 | to be decided |

Phases 9–11 are **optional** — see the cut order in [plan.md](../plan.md). The **Phase** column is the phase where the feature reaches ✅ — for the mock ones, the phase that replaces the fixture with real data.

## Mock fixtures still in the tree

Each of these is a promise to delete something:

| Fixture | Feeds | Removed in |
| --- | --- | --- |
| `dashboard.mock.ts` | dashboard stats + next reservation | Phase 9 |
| `myPoints.mock.ts` | `/my-points` list + stats | Phase 7 |
| `sessions.mock.ts` | `/sessions` history | Phase 9 |
