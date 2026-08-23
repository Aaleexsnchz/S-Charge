# Phase 6 — ETL reactivation + price model

**The goal: get the refresh scripts running on the server again, bring the prices current, and store what REVE actually publishes rather than a flattened approximation of it.**

The price model is built and shipped; the ETL is running. What remains is the drain finishing, the catalogue repair it revealed the need for, the UI, and a chosen cadence.

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Confirm the server matches the measurement | Done | host work |
| 2 | Remove the automatic watermark jump | Done | #37 |
| 3 | Advisory lock on the REVE tick | Done | #41 |
| 4 | Turn the scheduler on | **Draining** | host work |
| 4b | Record the catalogue drift, then repair it | **Ledger done** (#48), repair open | #48 |
| 5 | Model the tariff | Done | #43 |
| 6 | Use the model | Not started | — |
| 7 | Cadence and observation | Not started | host work |

## Closed slices — where their knowledge went

- **1 · Confirm the server.** Production matched the local snapshot to the microsecond on 2026-08-22. Nothing to carry.
- **2 · Remove the watermark jump.** A 504 records the error and holds position at any age; `--date-from` aims a probe. Rationale and the *camino no tomado*: [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).
- **3 · Advisory lock.** `reve_etl_lock` on its own connection, taken by both ETL scripts. Removed from [production-readiness.md](../production-readiness.md) and [Phase 13](../plan.md).
- **5 · Model the tariff.** Bands in `tariff_elements`, resolved price on the connector. Decision and rejected alternatives: [be-0003](../decisions/be-0003-price-on-the-connector.md). Measurements: [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md). Data-model shape: [modelo-de-datos.md](../thesis/modelo-de-datos.md).
- **4b · The ledger.** `reve_unmirrored_connectors` banks the ids and `tariff_raw` of connectors REVE serves and the mirror lacks; `--restart-cycle` rewinds an in-flight cycle. Operating both: [operations.md](../operations.md) → The REVE refresh. The findings: [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).

Shipped as `v0.1.2` (price model), `v0.1.3` (project rename), `v0.1.4` (ledger + scheduler as an ordinary service).

## Slice 4 — Turn the scheduler on

**Acceptance:** both jobs run unattended, the tariff drain completes, and `electricity_prices` reaches today.

Done: `v0.1.2` deployed with the lock and stall visibility; PVPC back to gap-free (5,639 rows, zero missing hours); the price migration verified on production; the scheduler started, then rewound to page 1 on 2026-08-23 14:30 UTC so the ledger could catch the 28 pages that drained before it existed.

- [ ] **The drain completes** — expected ~09:00–10:00 UTC on 2026-08-24. Watch with `refresh_reve --status`: `next page` climbing by 5/hour, `cycle end` frozen at `2026-08-23 09:12:55Z`, `last error` empty. On completion the watermark advances to the cycle start and `next page` resets to 1
- [ ] **Record what it cost** — pages, wall time, rows — against the 78 pages / 16 h / 7,760 rows estimate, in [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md)
- [ ] **Record the final catalogue backlog** (`--status`, first line). It sizes the repair below and is the input to Slice 7's cadence
- [ ] Confirm the hourly tick keeps PVPC current on its own now the backlog is cleared

## Slice 4b — Repair the catalogue

**Acceptance:** the backlog is seeded in and drains to ~0, and the connectors arrive priced rather than blank.

The ledger is shipped and filling. What remains is the pass that consumes it.

- [ ] **Probe the size first**: one call to `/locations?date_from=2026-06-09&page=20`. `date_from` returns every Location whose `last_updated` moved, and if that tracks EVSE status flicker rather than static edits, the "changed" set is most of the 137-page catalogue and this is not the cheap path. The spec hints at a split (`only_dynamic_info` is a separate filter; `Evse` carries its own `last_static_updated`) but a hint is not a measurement. Probe **after** the drain — same budget
- [ ] **`backend/scripts/backfill_locations.py`**, its own script rather than a fourth `REFRESH_PRIORITY` entry: a standing `/locations` refresh would compete with the tariff tick forever, while a repair ends when the backlog does
  - **`/cpos` first, then `/locations`, in that order.** `charging_points.party_id` is a foreign key to `cpos.party_id` and `_upsert_location` inserts what REVE sends with no guard. The CPO list is frozen at 2026-06-04, so a station from an operator that joined since raises a `ForeignKeyViolation` and **fails the whole tick** rather than skipping the row. Cheap — 142 CPOs is two pages — but not optional
  - **Takes `reve_etl_lock`**, which is what makes "shares the 5 req/hour budget" enforced rather than documented
  - **Resets the `/locations` cursor** (`next_page` → 1, `refresh_cycle_end` → null) before its first cycle. It currently reads `next_page = 5` with a `refresh_cycle_end` from a June cycle abandoned when the refresh was narrowed to tariffs; `_run_tick` resumes at `next_page` whenever that is set, so an unreset cursor starts a brand-new result set at page 5 and **silently skips pages 1–4**
  - `--budget` and `--status` as the other two scripts have them, so one interface reads across all three
- [ ] **For every backlog row whose connector now exists: apply `tariff_raw` and delete the row, in one transaction.** The delete belongs at the point of consumption, not on a periodic sweep — a sweep keyed on *"the connector exists now"* races this step, dropping the payload a moment before it is read and leaving the connector blank, which is the failure the ledger exists to prevent. A row whose connector arrived by another route is not a special case: the same loop applies a redundant price and clears it
- [ ] If the backlog does not reach zero, the residue is the case for one unfiltered `/connectors/tariffs` drain (469 pages, ~4 days), which returns every connector's current tariff regardless of change date

**Per-EVSE repair is closed off, not merely expensive.** `/evses/{evse_id}` returns no reference to its Location — no `location_id`, no address, no `party_id` — while `evses.charging_point_id` is `NOT NULL`. A new station's EVSE has nothing to attach to and no way to find its parent, which is 23 of every 30 backlog rows. The tariff feed's `evse_id` is REVE's internal UUID, not eMI3, so the operator cannot be recovered from a backlog row either and a `party_id`-filtered pass is not available.

## Slice 6 — Use the model

**Acceptance:** the map filter, the point detail and the simulator all answer with the price that actually applies, and free chargers say so.

- [ ] Map filter by **price now**, not by a minimum: `pricing_kind = 'free' OR current_price_per_kwh <= :max`. Without the `OR`, a price filter hides the free chargers — only 30 of them, but they are the ones a price filter is looking hardest for
- [ ] Point detail shows the band the driver is in, and that the price changes later — the difference between 0.25 and 0.47 is the app's whole argument
- [ ] **Free chargers labelled *gratis*** rather than "no price"
- [ ] Time- and session-priced connectors say how they are priced instead of showing nothing
- [ ] **A connector REVE priced at nothing and a connector REVE said nothing about are different, and must read differently.** *Gratis* is a fact from the source; 4,845 connectors with no tariff are an absence of information. **No estimated price is shown for the second** — an invented number next to a real one confuses the driver, and it is the same objection [be-0002](../decisions/be-0002-availability-not-modelled.md) raises against simulated availability. The simulator still reports time and energy for them, and simply has no cost
- [ ] **`unknown` is one driver-facing state, with exactly two messages.** 8,197 connectors have no resolvable price, from five causes — **4,845** REVE published no tariff for, **2,138** past their `valid_to`, **1,155** a record with no energy band, 52 with bands none of which apply now, 7 an implausible price. Four of those five mean the same thing to a driver and collapse to *el operador no publica precio*. The fifth is different and worth its own line:
- [ ] **An expired tariff says when it expired**: *la tarifa publicada caducó el 12/08/2026*. Stale is not the same as absent — it tells the driver the price was real once and is not to be trusted now, and it asserts no number. **This needs no backend change**: `TariffRead` already carries `valid_to`, so `pricing_kind === 'unknown'` plus a `valid_to` in the past is the whole condition. It is also the reason `valid_to` stays on `TariffRead` rather than being trimmed with the flattened columns
- [ ] Keep the reason derivation **in one place**. If a second consumer needs it, it becomes a computed field on `ConnectorRead` served by the backend, not a second copy of the rule — the whole point of [be-0003](../decisions/be-0003-price-on-the-connector.md) is that price semantics live where they can be tested
- [ ] **`PVPC + margen` survives as a recommendation, not as a displayed price.** `estimate_price` and the calibrated AC/DC margins stay for [Phase 7](../plan.md), where the owner of a private point is *offered* a price to set. That is a suggestion the owner accepts or overrides, not a number attributed to someone else's charger
- [ ] The simulator prices the actual charging window from the bands, spanning them where a charge crosses a boundary
- [ ] `just gen-api` — the response models change

## Slice 7 — Cadence and observation

**Acceptance:** both jobs run on a cadence that was chosen, and the phase's numbers are recorded.

- [ ] Choose the cadence per job and record why in [backend/crontab](../../backend/crontab). REE publishes the next day's PVPC once each evening, so hourly is ~23 wasted runs a day; the tariff refresh after the drain is asking about one hour of a ~7/hour change rate
- [ ] Both jobs observed running unattended for a day, with `last_error` empty
- [ ] **Re-run the unpriced census after the drain and record what moved.** The 8,197 split into what the ETL can repair and what it cannot, and the split is a measurement worth having: of the 1,155 unfilled records, **740 changed at source since the stall** and the drain should carry a real price for them. The **2,138 expired tariffs cannot be repaired at all** — every one was last touched at source on or before 2026-06-26, so a `date_from = 2026-07-08` window never returns them, and an unfiltered drain would only re-fetch the same expired row. That is a limit of the source, not of the ETL, and it belongs in the memoria as one
- [ ] The measured price-model numbers written into the memoria — see below

## For the memoria

All of these are written up in [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md); listed here only so the phase can be checked off against them.

- A national registry whose change-feed could not serve a window wider than a few hours, and which recovered without announcement — two measurements six weeks apart.
- Price varies by time of day **and** by connector power, nearly 2× on one tariff. This is what justifies a charging optimiser at a public point rather than only a domestic one.
- **In an open data feed, a zero is a claim only when the fields around it are populated too.** Reading the registry's blanks as *free* would have mislabelled 38× more chargers than are actually free.
- **An incremental `date_from` feed cannot repair data the source never touches**, so a mirror's freshness is bounded by the publisher's diligence rather than the puller's effort.
- **A log line is not a record**: one ordinary container recreation destroyed the drift measurement, which is why it now lives in a table.
- **Real-time availability is arithmetically impossible at 5 req/hour** — 42,088 EVSEs ÷ 100 ÷ 5 is 3.5 days per sweep. This corrects [be-0002](../decisions/be-0002-availability-not-modelled.md), which records the *absence of data* as the reason; the budget is the real one and the stronger argument.

## Open questions

- **Is `CONGESTION_TIME` worth pricing?** 218 band rows carry a component type absent from REVE's published enum. It is a surcharge, so it never outranks `ENERGY`, `TIME` or `FLAT`; a connector whose only applicable band is one resolves to `unknown`. Revisit if the drain makes it common.
- **`price` is ex-VAT per OCPI, and the app does not account for it.** 4,017 of 5,513 band rows carry a `vat`, mostly `21.00` — but **192 write `0.21`**, the same rate as a fraction, so any correction must normalise that first. Pre-existing, not introduced by the price model. Decide in [Slice 6](#slice-6--use-the-model) whether the app shows what the driver pays.
- **What catalogue cadence, now that drift is measured?** [Slice 7](#slice-7--cadence-and-observation), against the final backlog figure.

## Out of scope

- **Recovering tariff history.** No call shape returns it, and nothing in the app reads it.
- **Re-seeding the catalogue.** ~12 days under the rate cap; recovery is always a dump restore ([operations.md](../operations.md)).
- **Mirroring EVSE status.** See the memoria note above.

## Risks

- **The drain stalls on a 504 partway through.** Not destructive — the watermark holds and `failing_since` shows how long. Resume by re-probing with `curl` and waiting for REVE.
- **The `/locations` repair turns out to cost most of the catalogue.** That is what the probe is for, before any budget is committed.
- **`current_price_per_kwh` goes stale between recomputes.** It is a denormalisation of a band that changes on the hour, recomputed on the hourly tick. The simulator reads the bands directly and does not depend on it.
