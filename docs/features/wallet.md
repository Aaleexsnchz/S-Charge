# Wallet

**Status:** ⬜ Planned · **Phase** [10](../plan.md)

A simulated wallet and ledger so that charging at someone else's public point moves money: the driver is debited, the owner is credited, and both see the movement. No real payment processor — that is a [stretch goal](../ideas-backlog.md), and the simulation is stated as such in the thesis.

## Planned

A per-user balance derived from an append-only ledger (never a mutable column), a simulated top-up, transaction history for both sides, and owner revenue on `/my-points` computed from the ledger.

**Money exists before anything spends it**, which is why this lands before [sessions](sessions.md) rather than after: a session's first act is to hold funds, so there is nothing to build against until the ledger is there.

## Hold and settle

A [session](sessions.md) does not debit at the end; it **holds** the quoted amount when the driver confirms and **settles** when the charge stops — the final cost is taken and the remainder released. That is the flow real charging networks use, and it is what makes the ledger's hardest question disappear: because the quote is binding a session can only cost less than quoted, so the balance is checked once, at the hold, and never again.

Three kinds of movement, then: a top-up, a hold and its settlement, and the transfer to the owner of the point.

## Open questions for the phase plan

- Signed single-entry rows vs. paired double-entry movements.
- Whether a hold is a ledger row or a separate reservation against the balance — the second keeps the ledger a pure record of money that moved, at the cost of a second concept.
- Whether the platform takes a commission, which is the business-model argument but adds a third account.
