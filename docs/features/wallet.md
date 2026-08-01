# Wallet

**Status:** ⬜ Planned · **Phase** [10](../plan.md)

A simulated wallet and ledger so that charging at someone else's public point moves money: the driver is debited, the owner is credited, and both see the movement. No real payment processor — that is a [stretch goal](../ideas-backlog.md), and the simulation is stated as such in the thesis.

## Planned

A per-user balance derived from an append-only ledger (never a mutable column), a simulated top-up, transaction history for both sides, and owner revenue on `/my-points` computed from the ledger.

Open questions for the phase plan: signed single-entry rows vs. paired double-entry movements; what happens when the balance is insufficient (block at booking, block at completion, or allow negative); and whether the platform takes a commission, which is the business-model argument but adds a third account.
