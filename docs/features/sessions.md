# Charging sessions

**Status:** 🟡 Mock UI · **Real in** [Phase 11](../plan/plan.md)

One flow, from the quote a driver accepts to the money that settles when the charge ends: pick a connector, configure the charge, see what it will cost, confirm, and the session runs until it completes or the driver stops it early.

## Today

- **Backend** — nothing. There is no charging-session model.
- **Frontend** — `features/sessions` renders `sessions.mock.ts`, badged "datos de ejemplo".

## The flow (Phase 11)

1. **Configure.** At a point, the driver picks a connector, their vehicle and the SoC window — the inputs the [simulation](simulation.md) already takes.
2. **Quote.** The simulation returns duration, energy and cost, priced across the bands the charge will span.
3. **Confirm.** Accepting holds the quoted amount against the [wallet](wallet.md) balance. Declining costs nothing and leaves no record.
4. **Run.** The session is open until its planned duration elapses or the driver stops it.
5. **Settle.** The final cost is charged, the rest of the hold is released, and the session joins the driver's history and the owner's per-point usage.

## Why a session and not a booking

Reserving a point from the national catalogue is a promise no operator has agreed to keep — [REVE](points.md) knows nothing about this app, and a reservation it will not honour is worth nothing to the driver standing in front of an occupied charger. A session claims far less and is true: the driver plugged in, and this is what it cost. It needs no cooperation from the operator, so it works on the whole catalogue rather than only on user-registered points.

Reserving *ahead* remains defensible only for a point its owner controls. That is parked in [ideas-backlog.md](../ideas-backlog.md), not scheduled.

## The quote is binding

The session is priced at the bands quoted when the driver confirms, not re-priced at settlement. Two consequences, and the first is why the design is worth stating:

- **The hold is always at least the final cost.** A session can only end early, never late, so it can only cost less than quoted. There is no mid-session shortfall to handle, and no case where a driver owes more than they agreed to — the awkward question [wallet.md](wallet.md) asks about insufficient balance simply does not arise after the hold succeeds.
- **A tariff refresh mid-session does not move the price.** The ETL can rewrite a connector's bands at any hour; honouring the quote means a driver is never surprised by a number that changed while they were plugged in.

## Stopping early

The cost of a partial session is the energy actually delivered by the time it stopped, priced band by band. The charge model already reports when each step's energy arrives — it has to, in order to price a charge that crosses a band boundary — so a session stopped part-way is the same calculation truncated, not a second model.

## What it is honest about

- **Nothing measures the charge.** There is no hardware and no live feed, so energy is modelled from vehicle and connector specifications, and only wall-clock time is observed. A session is the model's prediction, recorded — which is why the model and the record must be one thing and not two.
- **A session ends by the clock, computed when it is read.** Not a timer and not a background job: a session that should have finished while the app was closed, or while the container was restarting, is finished.
- **The money is simulated**, and stated as such in the thesis. The *flow* — hold, settle, release — is the one real charging networks use.
- **Occupancy applies only to this app's own sessions.** Knowing a connector is busy because we started a session on it is not knowing whether it is busy in the world, and the UI must not blur the two. See [be-0002](../decisions/be-0002-availability-not-modelled.md).

## Open questions for the phase plan

- Whether a driver may hold more than one session open at a time, and whether a connector may.
- What happens to an abandoned session whose planned duration passed long ago — settle it silently on read, or surface it for the driver to confirm.
- Whether the owner of a point sees a session in progress or only completed ones.
