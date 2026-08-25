---
id: be-0004
status: proposed
phase: 10
date: 2026-08
related: [be-0002, be-0003]
---

# be-0004: A charging session is the quote the driver accepted, and the funds are held before it starts

**Decision.** Pre-charge simulation, session recording and payment are **one flow**, not three features: configure a charge at a connector → quote it → confirm or decline → run → settle. Confirming **holds** the quoted amount against the driver's wallet balance; the session is **priced at the bands quoted at that moment** and is never re-priced; it ends when its planned duration elapses or the driver stops it, and settlement charges the energy actually delivered and releases the rest. **Reserving a point ahead is not built at all** for the REVE catalogue.

**Rationale.** Nothing in this system measures a charge. There is no hardware and no OCPI `START_SESSION` feed, so energy delivered can never be observed and only wall-clock time can. A "recorded session" is therefore not a measurement that the simulation approximates — **it is the simulation, recorded**. Keeping them as separate features would mean two implementations of one model, guaranteed to drift, and the second one would have no better claim on the truth than the first.

Bookings fail for a different reason: they need a counterparty. Reserving a charger from the national catalogue is a promise no operator has agreed to keep, and a reservation that will not be honoured is worth nothing to a driver standing in front of an occupied point. A session asserts only what actually happened, needs no cooperation, and so works across the whole catalogue rather than only the handful of user-registered points.

**Consequences.**

- **The hold is always at least the final cost, so the balance is checked once.** A session can end early but never late, and the quote is binding, so its cost can only fall below what was held. The mid-session shortfall case does not exist and neither does an unpaid balance — which is what makes "block at booking, block at completion, or allow negative" a question that no longer needs answering.
- **A tariff refresh cannot move a price mid-session.** The ETL rewrites connector bands hourly; honouring the quote means a driver is never billed at a number that changed while they were plugged in. This is the same principle as [be-0003](be-0003-price-on-the-connector.md)'s refusal to show a price the source did not publish: what the app tells the driver has to be what the app then does.
- **Stopping early costs no new model.** The charge model already reports when each step's energy arrives, because a charge crossing a band boundary has to be priced band by band. A partial session is that same sum truncated at the stop time.
- **A session ends by the clock, computed on read.** Not a timer, not a background job — a session whose duration elapsed while the app was closed or the container was restarting is simply finished when next looked at. The alternative needs a scheduler to be correct, and the ETL already demonstrated what an unattended job costs to operate.
- **Occupancy becomes real, but only for our own sessions.** Knowing a connector is busy because this app started a session on it is not knowing whether it is busy in the world. [be-0002](be-0002-availability-not-modelled.md) still holds and the UI must not blur the two.
- **The wallet has to exist first**, since a session's first act is to hold funds. That inverts the previously planned order and makes the ledger a dependency of sessions rather than a later addition — including the offsite-backup obligation that arrives with the first balance a user cannot re-create.
- **The money is simulated and the flow is not.** Hold-then-settle is what real charging networks do. The thesis claims the mechanism, never the funds.

**Rejected alternatives.**

- *Bookings on the REVE catalogue, with sessions recorded from completed bookings.* The original plan. Rejected because the reservation half is unenforceable against operators who do not know this app exists, and restricting bookings to user-registered points — the honest version — would leave the feature exercisable on almost nothing.
- *Re-price the session at settlement from the live bands.* Arguably more "correct", and it manufactures a shortfall case: a hold taken against one price, settled against another the ETL wrote in between. It buys accuracy nobody asked for and costs the property that makes the ledger simple.
- *Debit at the end instead of holding at the start.* No hold means no balance check until the money is already owed, so the app must either allow a negative balance or refuse payment after the charge happened. Both are worse than declining before the driver plugs in.
- *Keep simulation, sessions and wallet as three features.* What the plan had. Rejected on the rationale above: with nothing measuring the charge, the "recording" feature would have to reimplement the "prediction" feature and would then disagree with the number the driver was shown.
- *Model a session as an owned resource with a real lock on the connector.* Would let the app enforce one session per connector globally. Rejected as a fiction: this app cannot observe or prevent a stranger charging at the same post, and enforcing exclusivity would present a guarantee it has no way to keep.

**References.**

- [features/sessions.md](../features/sessions.md) — the flow and its open questions.
- [features/wallet.md](../features/wallet.md) — hold and settle against the ledger.
- [be-0002](be-0002-availability-not-modelled.md) — why occupancy stays narrow.
- [be-0003](be-0003-price-on-the-connector.md) — where the quoted price comes from.
