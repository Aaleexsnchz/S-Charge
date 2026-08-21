# Smart home charging

**Status:** ⬜ Planned · **Phase** [8](../plan.md)

At a point the user owns, the cheapest way to charge tonight: given the PVPC curve, a departure time and the energy needed, when should the charge actually run, and what does waiting save.

## Planned

`POST /api/recommend` returning the cheapest schedule plus one or two alternatives and the saving against charging immediately, with a UI at an owned point and an algorithm chapter in [thesis/](../thesis/).

It depends only on [owner points](owner-points.md) (Phase 7) and the [price history](prices.md) (already shipped), which is why it is scheduled before bookings and the wallet: it is one of the thesis's evaluable algorithms and should not be what runs out of time.

Open questions for the phase plan: whether the schedule is one contiguous window or split slots across the night, and whether the vehicle's maximum power constrains it or the energy figure is taken as given.
