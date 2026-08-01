# Bookings

**Status:** ⬜ Planned · **Phase** [9](../plan.md)

Reserving a charging point for a time window, and the conflict rules that make a reservation mean something.

## Planned

`POST /api/bookings` with overlap detection, listing and cancelling own bookings, a `/bookings` screen, and the dashboard's next-reservation card on real data.

Open questions for the phase plan: booking granularity and limits (slot length, maximum duration, how far ahead, cancellation cutoff); what a booking means for availability when live availability is not modelled; and whether REVE-seeded points are bookable at all, given no real operator would honour it — restricting bookings to user-registered points is the more honest option.
