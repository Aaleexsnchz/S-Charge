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
- **2 · Remove the watermark jump.** A 504 records the error and holds position at any age; `--date-from` aims a probe. Rationale and the *camino no tomado*: [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).
- **3 · Advisory lock.** `reve_etl_lock` on its own connection, taken by both ETL scripts. Removed from [production-readiness.md](../production-readiness.md) and [Phase 13](../plan.md).
- **4 · The scheduler.** The drain completed: **7,774 rows in 78 pages**, against an estimate of 7,760 in 78 made from two calls — 0.2% out. The sizing technique, reusable for any paginated source with an ordered key and a hard quota, is in [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).
- **4b · Drift, and the repair.** `reve_unmirrored_connectors` banks the ids and `tariff_raw` of connectors REVE serves and the mirror lacks — **1,837** after a full drain. `/cpos` and `/locations` rejoined the refresh behind tariffs rather than becoming a separate repair script, and a `/locations` page that creates a connector settles its backlog row in the same transaction. Why the repair cannot enter through `/evses/{id}`, and why an incremental filter stops filtering at 77 days: [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md). Standing state: [features/points.md](../features/points.md). Operating it: [operations.md](../operations.md).
- **5 · Model the tariff.** Bands in `tariff_elements`, resolved price on the connector. Decision and rejected alternatives: [be-0003](../decisions/be-0003-price-on-the-connector.md). Measurements: [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md). Data-model shape: [modelo-de-datos.md](../thesis/modelo-de-datos.md).
- **6 · Use the model.** One derivation answers what a connector costs, the point detail shows the bands it is priced by, and the simulator prices the window a charge occupies instead of the instant it was asked about. `PVPC + margen` stopped being displayed as a price. Behaviour: [features/points.md](../features/points.md) and [features/simulation.md](../features/simulation.md). Concepts: [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md) and [simulacion-de-recarga.md](../thesis/simulacion-de-recarga.md).
- **7 · Cadence.** Chosen per target with the numbers behind each, encoded in `RefreshTarget` and [backend/crontab](../../backend/crontab): tariffs every tick, `/cpos` daily, `/locations` six-hourly. Priority order does the rest — the catalogue only ever gets what prices leave.

Shipped as `v0.1.2` (price model), `v0.1.3` (project rename), `v0.1.4` (ledger + scheduler as an ordinary service), `v0.1.5`–`v0.1.7` (ETL recovery and catalogue refresh).

## Still to observe

Neither blocks the phase; both want a day of ordinary running.

- **`/cpos` and `/locations` have not run yet.** Their cursors sit at the June seed because the tariff catch-up is still consuming the whole budget — the priority loop working as designed. Confirm they start once the tariff cycle drains, and that the backlog falls.
- **PVPC's cadence is provisional.** `0 9 * * *` is one useful run a day and no wasted ones, but the fetch also back-fills and nothing has tested a late REE publication. Decide against a real failure rather than in advance.
- **Re-run the unpriced census and record what moved.** The pre-drain 8,197 split into what the ETL could repair and what it could not; of the 1,155 unfilled records, 740 had changed at source. The 2,138 expired tariffs cannot be repaired at all — every one was last touched at source before the stall, so no `date_from` window returns them and an unfiltered drain would only re-fetch the same expired row. That is a limit of the source, and it belongs in the memoria as one.
