# Phase 6 — ETL reactivation + price model

**The goal: get the refresh scripts running on the server again, bring the prices current, and store what REVE actually publishes rather than a flattened approximation of it.**

Delivered. The ETL recovers from REVE's own failures and keeps the catalogue current; the tariff is stored as bands and resolved per connector; the app says what the price is, when it changes, and when it does not know.

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Confirm the server matches the measurement | Done | host work |
| 2 | Remove the automatic watermark jump | Done | #37 |
| 3 | Advisory lock on the REVE tick | Done | #41 |
| 4 | Turn the scheduler on | Done | host work |
| 4b | Record the catalogue drift, then repair it | Done | #48, #57 |
| 5 | Model the tariff | Done | #43 |
| 6 | Use the model | Done | #53 |
| 7 | Cadence and observation | Done | #57, #58 |

## Closed slices — where their knowledge went

- **1 · Confirm the server.** Production matched the local snapshot to the microsecond. Nothing to carry.
- **2 · Remove the watermark jump.** A 504 records the error and holds position at any age; `--date-from` aims a probe.
- **3 · Advisory lock.** `reve_etl_lock` on its own connection, taken by both ETL scripts. Removed from [production-readiness.md](../../production-readiness.md) and [Phase 14](../plan.md).
- **4 · The scheduler.** The drain completed: **7,774 rows in 78 pages**, against an estimate of 7,760 in 78 made from two calls — 0.2% out.
- **4b · Drift, and the repair.** `reve_unmirrored_connectors` banks the ids and `tariff_raw` of connectors REVE serves and the mirror lacks — **1,837** after a full drain. `/cpos` and `/locations` rejoined the refresh behind tariffs rather than becoming a separate repair script, and a `/locations` page that creates a connector settles its backlog row in the same transaction. Standing state: [features/points.md](../../features/points.md). Operating it: [operations.md](../../operations.md). Confirmed running: the first `/locations` page settled **198** banked rows in one transaction and took the backlog to **1,640**. The repair's real failure mode surfaced before its steady state did — a CPO REVE publishes without `city_code` stalled `/cpos` for seven hours and starved `/locations` behind it, because the tick walks its targets in dependency order and stops at the first error. Prices stayed perfectly current throughout, which is why nothing looked wrong.
- **5 · Model the tariff.** Bands in `tariff_elements`, resolved price on the connector. Decision and rejected alternatives: [be-0003](../../decisions/be-0003-price-on-the-connector.md). Data-model shape: [the thesis](../../thesis/S-Charge-TFM.pdf).
- **6 · Use the model.** One derivation answers what a connector costs, the point detail shows the bands it is priced by, and the simulator prices the window a charge occupies instead of the instant it was asked about. `PVPC + margen` stopped being displayed as a price. Behaviour: [features/points.md](../../features/points.md) and [features/simulation.md](../../features/simulation.md). Concepts: [the thesis](../../thesis/S-Charge-TFM.pdf).
- **7 · Cadence.** Chosen per target with the numbers behind each, encoded in `RefreshTarget` and [backend/crontab](../../../backend/crontab): tariffs every tick, `/cpos` daily, `/locations` six-hourly. Priority order does the rest — the catalogue only ever gets what prices leave. PVPC runs hourly rather than at a chosen hour, because it is a **day-ahead** market: the schedule catches a publication rather than sampling a moving value, and REE's release time can drift without anything to retune. Measured at 09:02 Madrid, the single morning run returned 24 hours for today and 0 for tomorrow against a 502 — structurally unable to hold tomorrow, which is every hour of an overnight charge. REE states its own release time in `attributes["last-update"]`, now stored per hour, so the publication moment never has to be inferred — and since REE restates days already published, it is also the only signal that a stored day has been superseded: [operations.md](../../operations.md).

Shipped as `v0.1.2` (price model), `v0.1.3` (project rename), `v0.1.4` (ledger + scheduler as an ordinary service), `v0.1.5`–`v0.1.7` (ETL recovery and catalogue refresh), `v0.2.0` (phase close) and `v0.2.1` (a CPO's descriptive fields are optional).

## Still to observe

It does not block the phase; it wants the drain to finish rather than more building.

- **Re-run the unpriced census and record what moved.** The pre-drain 8,197 split into what the ETL could repair and what it could not; of the 1,155 unfilled records, 740 had changed at source. The 2,138 expired tariffs cannot be repaired at all — every one was last touched at source before the stall, so no `date_from` window returns them and an unfiltered drain would only re-fetch the same expired row. That is a limit of the source, and it belongs in the memoria as one. A reading taken mid-drain already puts that bucket at **2,115**, so "cannot be repaired" is too strong: re-mirroring a connector can re-point it at a different, live tariff, moving the connector off the expired one without the tariff itself being refreshed. Confirm the mechanism before writing the claim down.
