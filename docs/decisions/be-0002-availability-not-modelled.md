---
id: be-0002
status: accepted
phase: 3
date: 2026-06
related: [be-0001, be-0004]
---

# be-0002: Do not model live availability — show points as available and say so

**Decision.** Whether a charging point is free or in use is **not modelled**. The `Evse.status` column and the per-point `aggregate_status` rollup exist and drive marker colour, but no source populates them, so points render as available. The application states this rather than disguising it, and the thesis names it as a limitation.

**Rationale.** REVE publishes no continuous status feed, and its per-EVSE status endpoint cannot be polled for ~42,000 EVSEs under a 5 req/hr quota ([be-0001](be-0001-reve-mirror-not-proxy.md)). That leaves inventing the data or leaving it empty.

Inventing it was planned twice and abandoned twice. First calibrated against ACN-Data, Caltech's historical charging-session dataset; that was dropped when the dataset proved to add nothing user-facing and never landed. Then as a lightweight synthetic occupancy model, seedable and plausible-looking by time of day. Both were rejected for the same reason: **they produce a number a user reads as real when it is not**, and the cost of explaining that distinction at the defense exceeds the demo value of coloured markers.

**Consequences.**

- The map's status filter is present but effectively inert until a real source exists. Keep it — it is wired to the same rollup a real feed would populate.
- **A reservation could never mean "this point is free now"**, only "this slot is reserved in our system", for a point nobody else can observe. [be-0004](be-0004-session-is-the-quote-it-accepted.md) resolves this by not building reservations at all: a session asserts only that a driver charged, and the occupancy it implies covers this app's own sessions alone.
- The honesty statement is load-bearing thesis content, not a caveat: it appears in `plan.md`, the data-model chapter, and the defense narrative.
- The schema is left ready for a real source — a CPO agreement, or REVE publishing a feed — with no migration required beyond writing to `Evse.status`.

**Rejected alternatives.**

- *Occupancy calibrated on ACN-Data.* Real-world grounding, but the dataset is Caltech campus parking: a distribution with no defensible mapping onto the Spanish public network. Blocked on access, and dropped in the scope pivot.
- *Lightweight synthetic occupancy.* Cheap and demo-friendly. Rejected: illustrative data indistinguishable from real data in the UI is the kind of thing that unravels under one question in a viva.
- *Hide the status dimension entirely.* Would remove the misleading signal, but also the extension point, and would leave the map visually flat with no way to reintroduce status later.
- *Poll REVE's per-EVSE status for a small subset.* Partial coverage is worse than none: users cannot tell which points have real status and which do not.

**References.**

- [thesis/modelo-de-datos.md](../thesis/modelo-de-datos.md) — *camino no tomado: la ocupación simulada*.
- [plan.md](../plan.md) → Data strategy.
