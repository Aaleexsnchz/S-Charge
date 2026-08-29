# Owner points

**Status:** 🟡 Mock UI · **Real in** [Phase 8](../plan.md)

The platform contribution: a user registers their own charging point, chooses whether it is publicly listed, prices it, and watches its usage. This is the first data in the system that REVE does not provide.

## Today

- **Backend** — `ChargingPoint.owner_user_id` exists on the model. Nothing else: no ownership endpoints, no visibility column, no owner pricing.
- **Frontend** — `features/my-points` renders the list and per-point stats from `myPoints.mock.ts`, badged "datos de ejemplo". The "Add" FAB shows "próximamente".

## Planned (Phase 8)

Point registration end to end, a public/private toggle that controls map visibility, owner pricing as `PVPC + margin` or a fixed €/kWh, and `/my-points` on real data with the mock deleted. Per-point usage stats follow with [session history](sessions.md); revenue follows the [wallet](wallet.md).

Open questions to settle when the phase is planned: whether user points reuse the full OCPI hierarchy or a simplified shape, how the owner sets the location (map pin vs. geocoded address), and whether ownership is verified at all.
