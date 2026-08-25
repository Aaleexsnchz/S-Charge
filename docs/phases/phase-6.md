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
| 6a | Say what the price model knows | **Done** | — |
| 6b | The bands a connector charges by | **Done** | — |
| 6c | Simulate on the bands | **Done** | — |
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

- [x] **Sized before budgeting**, 2026-08-25: pages 20 and 68 of `/locations?date_from=2026-06-09` both came back **full**, so at least 6,800 of 13,654 locations have "changed" since the seed. `last_updated` moves for nearly everything, so the filter is not a filter — **drain `/locations` plainly instead**: exactly 137 pages, bounded and complete, against ≥68 unbounded for a partial result. The same `date_from` that cannot be trusted on `/connectors/tariffs` ([operations.md](../operations.md) → What a `504` means)
- [ ] **`backend/scripts/backfill_locations.py`**, its own script rather than a fourth `REFRESH_PRIORITY` entry: a standing `/locations` refresh would compete with the tariff tick forever, while a repair ends when the backlog does
  - **`/cpos` first, then `/locations`, in that order.** `charging_points.party_id` is a foreign key to `cpos.party_id` and `_upsert_location` inserts what REVE sends with no guard. The CPO list is frozen at 2026-06-04, so a station from an operator that joined since raises a `ForeignKeyViolation` and **fails the whole tick** rather than skipping the row. Cheap — 142 CPOs is two pages — but not optional
  - **Takes `reve_etl_lock`**, which is what makes "shares the 5 req/hour budget" enforced rather than documented
  - **Resets the `/locations` cursor** (`next_page` → 1, `refresh_cycle_end` → null) before its first cycle. It currently reads `next_page = 5` with a `refresh_cycle_end` from a June cycle abandoned when the refresh was narrowed to tariffs; `_run_tick` resumes at `next_page` whenever that is set, so an unreset cursor starts a brand-new result set at page 5 and **silently skips pages 1–4**
  - **No `date_from`** — see above; the filter does not filter here. `--budget` and `--status` as the other two scripts have them, so one interface reads across all three
- [ ] **For every backlog row whose connector now exists: apply `tariff_raw` and delete the row, in one transaction.** The delete belongs at the point of consumption, not on a periodic sweep — a sweep keyed on *"the connector exists now"* races this step, dropping the payload a moment before it is read and leaving the connector blank, which is the failure the ledger exists to prevent. A row whose connector arrived by another route is not a special case: the same loop applies a redundant price and clears it
- [ ] If the backlog does not reach zero, the residue is the case for one unfiltered `/connectors/tariffs` drain (469 pages, ~4 days), which returns every connector's current tariff regardless of change date

**One page seeds a hundred stations, so the grouping is already right.** A `/locations` item carries the whole nesting — station → EVSEs → connectors — so one call creates ~100 points, ~308 EVSEs and ~342 connectors. By the mirror's ratios (3.08 EVSEs per point, 1.11 connectors per EVSE) the 1,837 backlog connectors span roughly 1,650 EVSEs across ~535 stations, about 4 % of the catalogue. At 4 calls an hour beside the tariff tick, 137 pages is ~34 hours unattended.

**Per-EVSE repair is closed off, not merely expensive.** `/evses/{evse_id}` returns no reference to its Location — no `location_id`, no address, no `party_id` — while `evses.charging_point_id` is `NOT NULL`. A new station's EVSE has nothing to attach to and no way to find its parent, which is 23 of every 30 backlog rows. The tariff feed's `evse_id` is REVE's internal UUID, not eMI3, so the operator cannot be recovered from a backlog row either and a `party_id`-filtered pass is not available.

## Slice 6a — Say what the price model knows

**Acceptance:** no surface shows an em dash where the model has a fact, and no surface shows a number the source did not publish.

Done. `features/points/display.ts` derives one `PricingState` per connector and every price render goes through it — the point detail, the map sheet and the dashboard's nearby cards, which each derived their own before.

- The **map filter** needed no work: `pricing_kind = 'free' OR current_price_per_kwh <= :max` was already in both `services/points.py` and `map/filters.ts`, and the GeoJSON already carries `has_free`.
- **Free chargers say *gratis***, and a point whose cheapest connector is free leads with it — free outranks any price in the point-level summary, the same rule the map filter applies.
- **Time- and session-priced connectors say how they are priced** instead of showing nothing.
- **`unknown` is one state with two messages.** Four of its five causes collapse to *el operador no publica precio*; an expired tariff instead says *la tarifa publicada caducó el 12/08/2026*. Stale is not absent — it says the price was real once and is not to be trusted now, and it asserts no number. No backend change was needed: `TariffRead` already carried `valid_to`, which is why it survived the flattening.
- **No estimate fills the gap.** The 4,845 connectors REVE published no tariff for get no invented price.

## Slice 6b — The bands a connector charges by

**Acceptance:** the point detail shows the price now *and* what it will be later, so a driver can decide to wait.

Done. `GET /api/points/{id}` carries `price_schedules` — the day's energy bands per connector, already power-gated, with exactly one marked current; the detail page renders them as a table with the current row highlighted.

- **On the detail response, not on `ConnectorRead`.** `GET /points` takes a bbox and has no limit, so a schedule on the *shared* connector model would resolve bands for every connector in the viewport to serve a list that shows none — the alternative [be-0003](../decisions/be-0003-price-on-the-connector.md) rejected as "resolve the price on every read". A `PointDetailRead` subclass confines it to the one-point endpoint, which measured 1–2 ms against that endpoint's 5 ms. A separate endpoint would have bought nothing for a second round trip on a phone at the charger.
- **The band-matching rules are not duplicated.** The resolver's source, restriction predicates and restriction columns are module-level SQL fragments that both the hourly recompute and the schedule compose. Checked estate-wide: over 1,316 connectors at all 286 points that price by time, the schedule's current band and the stored `current_price_per_kwh` never disagree.
- **Two bugs the real data caught, neither visible in a unit test.** The tariff's unrestricted fallback listed itself as an all-day band beside the real windows, and REVE's inclusive end bounds made 18:00 belong to both `00:00-18:00` and `18:00-22:00`, highlighting two prices at once. The fallback is now dropped wherever real windows exist, and the current band breaks its tie the way the resolver breaks it.
- **Connectors are grouped by identical schedule.** One measured point has 18 connectors on one schedule; per-connector rendering would repeat the table 18 times. The 8% of points whose connectors differ keep a table each, because the connector is the grain where the price is unique.

## Slice 6c — Simulate on the bands

**Acceptance:** the simulator prices the real charging window, and never attributes an estimate to an operator.

Done. Measured on a real AC connector, the same 42 kWh charge costs **13,21 €** started at 10:00 and **14,86 €** started at 21:00 — 12.5% apart on when the driver plugs in, which is the argument the app exists to make.

- **The window is priced a minute at a time**, composed from the fragments [6b](#slice-6b--the-bands-a-connector-charges-by) added: `_LOCAL_TS_SERIES` generates the session's minutes where the other two statements take one instant, so the band rules are still written once. The physics loop now reports when each SoC step's energy arrives, and each step pays the band covering that moment.
- **A row per minute, not a band intersection.** The bands a session crosses are few, but DC power tapers, so energy is not spread evenly across them — the cost has to weight each minute by the energy actually delivered in it.
- **The result reports the effective price**, the cost divided by the energy priced. Quoting a band for a charge that crossed two would be a number no meter reads.
- **`price_source`, `pvpc_per_kwh` and `margin_per_kwh` are gone from `SimulationResult`.** With the estimate no longer served, `price_source` had one possible value; keeping the enum would be an interface for a requirement nobody has.
- **`services/price_suggestion.py` now has no caller and stays anyway**, which its module docstring records so the next reader does not delete it. `PVPC + margen` is the suggestion an owner gets in [Phase 7](../plan.md) when pricing their own point.
- **The bug the fixtures could not show**: `generate_series` starts at the instant it is given, so a session beginning at 14:32:07 produced minute keys carrying those seconds while the lookup truncated them — no minute ever matched and every charge came back unpriced. Both ends now floor to the minute.

## Slice 7 — Cadence and observation

**Acceptance:** both jobs run on a cadence that was chosen, and the phase's numbers are recorded.

- [x] **REVE's cadence is decided and encoded** in `RefreshTarget`, with the numbers behind each choice: tariffs every tick, `/cpos` daily (one changed in June, one in March), `/locations` six-hourly (~88 change a day, so an hourly window holds four). Priority order does the rest — the catalogue only ever gets what prices leave
- [ ] **PVPC's cadence is still open.** REE publishes the next day once each evening, so `0 9 * * *` is one useful run and no wasted ones — but the fetch also back-fills, and nothing has tested what happens when REE is late. Decide against a real failure rather than in advance
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
- **`price` is ex-VAT per OCPI, and the app does not account for it.** 4,017 of 5,513 band rows carry a `vat`, mostly `21.00` — but **192 write `0.21`**, the same rate as a fraction, so any correction must normalise that first. Pre-existing, not introduced by the price model. Decide in [Slice 6b](#slice-6b--the-bands-a-connector-charges-by) whether the app shows what the driver pays.
- **What catalogue cadence, now that drift is measured?** [Slice 7](#slice-7--cadence-and-observation), against the final backlog figure.

## Out of scope

- **Recovering tariff history.** No call shape returns it, and nothing in the app reads it.
- **Re-seeding the catalogue.** ~12 days under the rate cap; recovery is always a dump restore ([operations.md](../operations.md)).
- **Mirroring EVSE status.** See the memoria note above.

## Risks

- **The drain stalls on a 504 partway through.** Not destructive — the watermark holds and `failing_since` shows how long. Resume by re-probing with `curl` and waiting for REVE.
- **The `/locations` repair turns out to cost most of the catalogue.** That is what the probe is for, before any budget is committed.
- **`current_price_per_kwh` goes stale between recomputes.** It is a denormalisation of a band that changes on the hour, recomputed on the hourly tick. The simulator reads the bands directly and does not depend on it.
