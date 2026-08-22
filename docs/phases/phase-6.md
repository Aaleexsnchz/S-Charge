# Phase 6 — ETL reactivation + price backfill

**The goal: get the refresh scripts running on the server again, backfill the prices if REVE will serve them, and show real price data.** Nothing else.

Both ETLs stopped when the laptop's containers did, and [Phase 5](phase-5.md) deployed with the `scheduler` service **deliberately stopped** so the state could be inspected before anything overwrote it. Prices model and the earlier 504 measurements: [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md). Mirror-not-proxy: [be-0001](../decisions/be-0001-reve-mirror-not-proxy.md).

## What we actually have

Measured on the **local** database, 2026-08-22. The VPS was restored from `ev_charging_seed_20260803T070005Z.dump` and has run no ETL since, so it should match — [Slice 1](#slice-1--confirm-the-server-matches-the-measurement) confirms rather than assumes.

| Data | State | Stale since | Age |
| --- | --- | --- | --- |
| PVPC prices | 5111 rows, **continuous — no gaps** | 2026-08-01 21:00 UTC | 21 days |
| REVE tariffs | watermark `2026-07-08 19:30:03`, `last_error` = 504 | 2026-07-08 | 45 days |
| Catalogue (`/cpos`, `/locations`) | frozen at the seed — **by design**, not a failure | 2026-06-09 / 06-21 | ~62 days |

**13,654** charging points · 42,088 EVSEs · 46,808 connectors · 142 CPOs · 2,126 tariffs.
Coverage: **11,288** points fully priced · **1,504** partly · **862** with no priced connector.

**The 862 are unpriced at source.** The seed drained `/connectors/tariffs` unfiltered, so REVE was asked for every connector's tariff and returned none for these. They are not stale in our copy — their CPO publishes no price.

### Two ways to backfill, and the cheap one is tried first

`/connectors/tariffs` takes an **optional** `date_from`.

**With `date_from = 2026-07-08`** REVE returns only what changed since — at the churn measured before the stop (single digits a day) that is a few hundred connector-tariffs, a handful of pages, and the gap closes in about an hour. This is the outcome worth having.

**The risk is the 504.** It is not caused by the result being large; it is REVE's *scan* for "what changed since X", which gets more expensive the wider the window. The prior measurement ([precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md)) is unambiguous: `date_from` at ~100 h and ~20 h both 504, `now − 3 h` returns 200. At 45 days the window is far outside anything that has ever worked — but the regression has self-healed once before, and the probe is one call.

**Without `date_from`** the endpoint returns every connector's current tariff, paginated at 100. That is what the seed did, so it is a proven call shape rather than a hopeful one — and it asks a different question, so it does not fail for the reason above. The cost is arithmetic: **46,808 ÷ 100 = 469 pages ÷ 5 req/hr ≈ 3.9 days** of resumable drain. It recovers every *current* price; it cannot recover intermediate history, and neither can anything else.

So [Slice 4](#slice-4--backfill-the-prices) is a decision tree, cheapest first, with a fallback that cannot fail the same way.

### The automatic jump goes

`_handle_server_error` currently jumps a *stale* watermark to `now − REVE_REFRESH_LOOKBACK_HOURS` (2 h) and records the skip, keeping only a *recent* one for retry. At 45 days the jump condition is met, so one unattended tick would discard the pre-gap position. July survived only because the 504 hit while the watermark was 2 hours old and was classed transient — which is why the data is still recoverable today.

**The jump is removed, not bounded.** It exists to keep the refresh moving by writing history off, and **the goal here is the opposite: get all the data.** A 504 should leave the watermark where it is and say so, exactly as it did in July — the behaviour that preserved the position rather than the behaviour that would have destroyed it.

The cost is honest and worth stating: with the jump gone, a watermark that REVE will not serve makes every tick spend one call on a 504 and never self-heal. That is the intended trade — it is visible and recoverable, where a silent skip is neither — and after [Slice 4](#slice-4--backfill-the-prices) the watermark is current, so it should not arise.

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Confirm the server matches the measurement | Not started | host work |
| 2 | Remove the automatic watermark jump | Done | #37 |
| 3 | Advisory lock on the REVE tick | Not started | — |
| 4 | Backfill the prices | Not started | host work |
| 5 | PVPC current again | Not started | host work |
| 6 | Say when a point has no price | Not started | — |
| 7 | Scheduler on, cadence chosen, observed | Not started | host work |

**1 → 2 → 3 before 4.** The backfill may be a multi-day writer against the cursor; the guard and the lock exist so it cannot be corrupted halfway. 5 and 6 are independent. **7 is last** — the ordinary hourly refresh only makes sense once the prices are current.

## Decisions taken

- **Try `date_from` first, fall back to an unfiltered drain.** The alternative considered and dropped was binary-searching for the oldest servable `date_from`. It recovers a *subset* at more risk than the unfiltered drain recovers *everything*, so it only ever made sense when the unfiltered path had been overlooked.
- **The analysis runs against the local database; the server is only confirmed against it.** Same dump, no ticks since, so the cheap check is a comparison. The **server is the source of truth** for anything that will be advanced.
- **Unpriced points are shown and labelled, not hidden and not deleted.** A point that exists is worth showing even when its price is unknown — a driver standing next to it still needs to know it is there. This matches [be-0002](../decisions/be-0002-availability-not-modelled.md)'s rule for availability: show the thing, and say plainly what is not known about it.

## Slice 1 — Confirm the server matches the measurement

**Acceptance:** the production cursor and row counts either match the table above, or the difference is written down.

- [ ] On the host: the same cursor and count queries, compared against the figures above
- [ ] Confirm `scheduler` is still absent from `docker compose ps`
- [ ] Any divergence recorded here — it would mean the restore or the deploy touched data, which nothing in [Phase 5](phase-5.md) should have

## Slice 2 — Remove the automatic watermark jump

**Acceptance:** no unattended tick can discard a watermark, at any age, and `2026-07-08 19:30:03` is recorded permanently regardless.

- [x] Recorded the pre-reactivation cursor in [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md), with the jump written up there as a *camino no tomado*
- [x] **Removed the automatic jump.** A 504 records the error and leaves the watermark, whatever its age. `skip_refresh_window` is gone with it
- [x] `REVE_REFRESH_LOOKBACK_HOURS` removed — nothing jumps to it any more, so it meant nothing
- [x] `--date-from` on `refresh_reve.py`, so [Slice 4](#slice-4--backfill-the-prices) aims a probe without editing `reve_etl_cursor`
- [x] `--status` now prints `last_error`, and the 504 goes to stderr. A stale watermark costs one call per tick until an operator acts, so the stall has to be visible
- [x] The two jump tests replaced by one parametrised over recent / stale / very-stale ages, all asserting the watermark does **not** move

## Slice 3 — Advisory lock on the REVE tick

**Acceptance:** two concurrent refresh runs cannot corrupt the cursor; the second exits quietly.

`reve_etl_cursor` is one row per endpoint, read-modify-written every tick. Two writers corrupt it — and [Slice 4](#slice-4--backfill-the-prices) may run for days, which is days of exposure to a stray manual run or an accidentally-enabled cron.

Listed under [Phase 13](../plan.md) in [production-readiness.md](../production-readiness.md); it belongs here, because this phase is what makes it likely rather than theoretical.

- [ ] Postgres advisory lock at the top of `_run_tick`, exiting quietly if another run holds it
- [ ] A test proving the second runner exits without writing
- [ ] Remove the item from [production-readiness.md](../production-readiness.md)'s Phase 13 list

## Slice 4 — Backfill the prices

**Acceptance:** every connector's price is as current as REVE will serve, and the watermark is set forward so the ordinary refresh takes over cleanly.

Cheapest path first. Each probe is one call against a 5/hr budget.

- [ ] **Probe A — `date_from = 2026-07-08 19:30:03`, page 1.** If `200`, drain the pages under budget and the gap closes in about an hour. This is the good outcome and costs one call to find out
- [ ] **Probe B — no `date_from`, page 1.** Only if A returns 504. If `200`, run the full ~469-page drain across ticks, checking progress daily rather than watching it
- [ ] **If both 504**, REVE is degraded beyond either path. Record it, leave the watermark alone, and re-probe another day — this is the only branch where the phase waits on somebody else
- [ ] On success by either path, set `refresh_watermark` to the instant the backfill **started**, so the first ordinary tick asks for changes since then and nothing is skipped
- [ ] Record which path worked and what it cost in [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md) — the 504's behaviour over time is thesis material, and this is a second data point on it
- [ ] Re-measure the 862 / 1,504 / 11,288 coverage split afterwards

## Slice 5 — PVPC current again

**Acceptance:** `electricity_prices` reaches today and `/api/prices/today` leaves its empty state.

The low-risk half of the phase, independent of everything REVE. `fetch_pvpc.py` takes no arguments and gap-backfills from the last stored hour, so one run closes 21 days.

- [ ] One manual run on the host
- [ ] Verify the curve is still continuous afterwards — the gap query must return zero rows
- [ ] Confirm the dashboard and prices views render real data

## Slice 6 — Say when a point has no price

**Acceptance:** a point with no priced connector appears on the map and in search exactly as any other, and its detail view states that no price is published for it. Nothing is hidden and nothing is deleted.

The 862 are unpriced **at source** — the seed asked REVE for every connector's tariff and got none for them. That is information about the point, not a defect in our copy, and it can change the moment their CPO publishes one.

Showing them is also the honest option: a driver next to a charger needs to know it exists. Hiding it would make the map claim the station is not there; deleting it would make that permanent, against a catalogue that costs ~12 days to rebuild.

- [ ] Point detail says no price is published, rather than rendering an empty or zero price
- [ ] The simulator refuses the cost estimate for such a point and says why, instead of computing against a missing tariff
- [ ] Any list or sort by price puts them last rather than treating a missing price as free
- [ ] Run [Slice 4](#slice-4--backfill-the-prices) first, so the number is the current one
- [ ] Record the count in the memoria: how much of a national registry carries no public price is a finding about the Spanish charging network, not a detail about this app

## Slice 7 — Scheduler on, cadence chosen, observed

**Acceptance:** both jobs run unattended on the server, and the cadence is a decision rather than an inheritance.

The current crontab is hourly for both, chosen when the laptop was the host. Two things changed: REE publishes the next day's PVPC once, in the evening, so hourly is ~23 wasted runs a day; and after the backfill the tariff refresh is asking "what changed in the last hour", which measured at single digits per day.

- [ ] Choose the cadence for each job and record why in [backend/crontab](../../backend/crontab)
- [ ] `--profile scheduler up -d` on the host. **Repeat it on every subsequent `up`** — the profile is not sticky ([operations.md](../operations.md))
- [ ] First ticks confirmed in the container logs for both jobs
- [ ] No 504s in the first ticks — after the backfill the watermark is current, so a `last_error` appearing means the window has gone stale again and needs an operator
- [ ] `electricity_prices` reaching today, and still there a day later

## For the memoria, not for this phase

Two constraints this phase runs into are worth a paragraph in the thesis rather than work here.

- **Real-time availability is impossible at 5 req/hr.** `/evses/operational_status` exists and takes `date_from`, so the data is there — but **42,088 EVSEs ÷ 100 = 421 pages ÷ 5 req/hr = 3.5 days for one full sweep**, and per-EVSE lookups are worse: 5 points an hour against a network with thousands of transactions. So availability in this app comes from its own bookings and sessions, and the honest account is that a real deployment solves it with CPO agreements or a feed built for the purpose, not with a public registry's rate limit. This corrects [be-0002](../decisions/be-0002-availability-not-modelled.md), which records the *absence of data* as the reason — the budget is the real one, and the stronger argument.
- **The 504 itself.** A public national registry whose change-feed cannot serve a window wider than a few hours is a finding about the data source, and it is what shaped this entire ETL.

## Open questions

- **Does the frozen catalogue stay frozen?** `/cpos` and `/locations` have not moved since June and drift by a day every day. It was right under a laptop's budget; after the backfill the ordinary tariff tick needs only a few calls a day, so a weekly catalogue pass may now fit inside the same cap. Decide once [Slice 7](#slice-7--scheduler-on-cadence-chosen-observed) has a real call-usage figure.

## Out of scope

- **Recovering tariff history.** No call shape returns it, and nothing in the app reads it.
- **Re-seeding the catalogue.** ~12 days under the rate cap; recovery is always a dump restore ([operations.md](../operations.md)).
- **Mirroring EVSE status.** See the memoria note above.

## Risks

- **Both probes 504** and the backfill cannot run at all. The phase still delivers: PVPC current, scheduler running, prices as good as REVE allows. The gap becomes a measured finding rather than a fixed problem.
- **A stray writer corrupts the cursor during a multi-day drain.** Mitigated by Slice 3 landing first, and the scheduler staying stopped until Slice 7.
- **The scheduler is started before Slice 2.** The only irreversible step in the phase: while the jump still exists, one tick writes the watermark off. Slice 1 checks the container is still absent for exactly this reason.
