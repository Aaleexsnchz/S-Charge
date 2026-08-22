# Phase 6 — ETL reactivation + price model

**The goal: get the refresh scripts running on the server again, bring the prices current, and store what REVE actually publishes rather than a flattened approximation of it.**

Both ETLs stopped when the laptop's containers did, and [Phase 5](phase-5.md) deployed with the `scheduler` service **deliberately stopped** so the state could be inspected before anything overwrote it. Prices model: [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md). Mirror-not-proxy: [be-0001](../decisions/be-0001-reve-mirror-not-proxy.md). The vendored REVE spec is [reve-api-spec.json](../reve-api-spec.json).

## What we measured

Database inventory taken 2026-08-22, local and production **identical to the microsecond** ([Slice 1](#slice-1--confirm-the-server-matches-the-measurement)).

| Data | State | Stale since |
| --- | --- | --- |
| PVPC prices | 5111 rows, **continuous — no gaps** | 2026-08-01 21:00 UTC |
| REVE tariffs | watermark `2026-07-08 19:30:03`, `last_error` = 504 | 2026-07-08 |
| Catalogue (`/cpos`, `/locations`) | frozen at the seed — **by design**, not a failure | 2026-06-09 / 06-21 |

**13,654** points · 42,088 EVSEs · 46,808 connectors · 142 CPOs · 2,126 tariffs · 41,963 connectors priced.

Two live probes against REVE on 2026-08-22 (2 of the 5/hour budget) established the rest.

### The 504 has healed; the gap is ~16 hours of drain

`date_from = 2026-07-08T19:30:03Z` now returns **HTTP 200 in 16.5 s** with a full page. The wide-window regression that froze the watermark in July is gone — this is the second observation of that failure self-healing, and worth recording as such.

Results are ordered by **`connector_id` ascending**. Page 1 covered 1.303 % of the id space and page 77 ended at 99.18 %, two independent estimates agreeing on **~7,760 rows ≈ 78 pages ≈ 16 h** at 5 requests/hour. Pages 1 and 77 share zero rows.

**~0.7 % of rows will be skipped, and that is accepted.** Churn is **172 connector-rows/day**. Over a 16-hour drain ~115 new rows enter a set ordered by a stable key, and those sorting before the cursor push roughly 57 rows past it. They are *not* recovered by the next cycle — the watermark advances to cycle start, so a skipped row whose change predates that only returns when its connector next changes, ~45 days out. The alternative is the unfiltered drain: a stable 46,808-row set with no insertion risk, but 469 pages and ~4 days. Three extra days to save 57 stale prices is the wrong trade.

### The stored price is a flattened approximation, and sometimes cannot be right

A real tariff from the probe — one connector, nine elements:

| Connector power | 00:00–06:59 | 07:00–22:59 | 23:00–23:59 |
| --- | --- | --- | --- |
| ≤ 22 kW | 0.25 | 0.29 | 0.25 |
| ≤ 100 kW | 0.31 | 0.37 | 0.31 |
| ≤ 450 kW | 0.40 | **0.47** | 0.40 |

`_energy_price_component` takes the **first** ENERGY component it meets and discards the restrictions, so this stores `0.31`. A charge at 20:00 on a 450 kW connector is costed **34 % low**.

Price varies along two axes, and the second is decisive: **44 time-varying tariffs are shared across connectors of different power, covering 6,347 connectors.** For those, one `price_per_kwh` on the tariff row is not imprecise but *structurally incapable* of being correct, because connectors sharing that tariff legitimately have different prices. The denormalised price has to live on the **connector**, which is the grain at which the answer is unique. All 46,808 connectors have `max_electric_power` populated, so it always resolves.

Scale, weighted by connector rather than by tariff: **7,175 of 41,963 priced connectors (17.1 %)** sit on a time-varying tariff today. The fresh probe skews far higher because it samples connectors *whose tariff changed*, which over-represents CPOs that actively manage prices; the figure will rise after the drain but not to that level.

### 1,152 connectors are free and the app says "no price"

`price_per_kwh IS NULL` currently conflates four different facts. Of the 1,195 connectors on a tariff with no per-kWh price:

- **1,152 are free** — `FLAT 0.0` or `TIME 0.0`
- ~43 are priced by time or session (TIME €0.17–3.85/h, FLAT €0.77)
- 1 carries `ENERGY 9110.66`, bad data at source, correctly rejected by `_plausible_price`

For a driver, free is the most useful price there is, and it is the one the app currently hides.

### Nothing needs re-fetching to fix the model

**All 2,126 tariffs hold their complete `elements` array in `raw_data`**, including rows last refreshed on 10 June — verified, zero empty. The flattening happens on the way *out*, never on the way in. So the price model can be built and backfilled from the database with no network calls, in parallel with the drain.

Restrictions are resolvable without a session in ~99.6 % of cases: across 200 sampled connectors, `start_time`/`end_time` 1364, `day_of_week` 1165, `max_power` 1161, `start_date`/`end_date` ~200, against `min_duration` 4 and `max_duration` 1. The session-dependent handful is why the denormalised price is *"price now, absent session-dependent restrictions"* and the simulator — which knows the session — can do better.

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Confirm the server matches the measurement | Done | host work |
| 2 | Remove the automatic watermark jump | Done | #37 |
| 3 | Advisory lock on the REVE tick | Done | #41 |
| 4 | Turn the scheduler on | Not started | host work |
| 5 | Model the tariff | Not started | — |
| 6 | Use the model | Not started | — |
| 7 | Cadence and observation | Not started | host work |

**4 and 5 run in parallel.** The drain is a cron ticking for 16 hours; Slice 5 is desk work against `raw_data` and needs no network. 6 depends on 5; 7 closes the phase.

## Decisions taken

- **Backfill by `date_from`, not by an unfiltered drain.** Measured: 16 h against ~4 days, for a 0.7 % skip rate. Recorded above with the arithmetic.
- **Let the scheduler do the drain.** It is safe now — the watermark cannot be jumped ([#37](https://github.com/Aaleexsnchz/S-Charge/pull/37)) and concurrent writers cannot corrupt the cursor ([#41](https://github.com/Aaleexsnchz/S-Charge/pull/41)) — and 5 calls/hour against ~78 pages is exactly the 16 hours needed. Draining by hand would spend the same budget with more chances to get it wrong.
- **`tariffs.price_per_kwh` is dropped, not redefined.** A tariff shared across connectors of different power cannot carry one correct price. Replaced by `connectors.current_price_per_kwh` plus `connectors.pricing_kind`.
- **Unpriced points are shown and labelled, never hidden or deleted.** A point that exists is worth showing even when its price is unknown, and 1,152 of them turn out to be free. Matches [be-0002](../decisions/be-0002-availability-not-modelled.md)'s rule for availability.

## Slice 1 — Confirm the server matches the measurement

**Acceptance:** production either matches the inventory above, or the difference is written down.

- [x] Cursor and counts compared on the host, **2026-08-22: no divergence**, every field identical to the microsecond
- [x] `scheduler` absent; `db` uptime two weeks against fourteen hours for the app containers, so CD recreated only what changed
- [x] Nothing to record — the seed dump, the restore and every deploy since left the data identical

## Slice 2 — Remove the automatic watermark jump [x]

A 504 records the error and leaves the position alone at any age. `skip_refresh_window` and `REVE_REFRESH_LOOKBACK_HOURS` are gone with it, `--status` prints `last_error`, and `failing_since` / `consecutive_failures` answer *how long has this been broken* — which `last_attempted_at` never could. `--date-from` aims a run at a chosen window.

**One gap left open deliberately:** `--date-from` does not imply dry-run. A *successful* run still calls `record_refresh_progress`, so probing with the script can advance the cursor. Probe with `curl` until a `--dry-run` exists.

## Slice 3 — Advisory lock on the REVE tick [x]

`reve_etl_lock` taken by both `refresh_reve` and `seed_reve`, on **its own connection** — a session hands its connection back to the pool on commit, so a session-level lock works only by accident in a single-threaded script. A second runner exits 0, makes no REVE call, and writes nothing. Removed from [production-readiness.md](../production-readiness.md) and [Phase 13](../plan.md).

## Slice 4 — Turn the scheduler on

**Acceptance:** both jobs run unattended, the tariff drain completes, and `electricity_prices` reaches today.

- [ ] Deploy current `main` first — the scheduler must be running the code with the jump removed and the lock in place
- [ ] `--profile scheduler up -d` on the host. **Repeat it on every subsequent `up`** — the profile is not sticky ([operations.md](../operations.md))
- [ ] PVPC current within one tick; verify the curve is still gap-free afterwards
- [ ] Watch the tariff drain across ~16 h with `just etl-status`: `next_page` climbing, `refresh_cycle_end` frozen, `last_error` empty
- [ ] On completion the watermark advances to the cycle start and `next_page` resets to 1
- [ ] Record what the drain actually cost — pages, wall time, rows — against the 78/16 h/7,760 estimate, in [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md)

## Slice 5 — Model the tariff

**Acceptance:** the price bands REVE publishes are stored as queryable rows, and every connector carries a price that is correct for it.

Needs no network: backfilled from `raw_data` for all 2,126 existing tariffs, and populated by the ETL from then on.

- [ ] **`tariff_elements`** — one row per price component: `tariff_id`, `component_type`, `price`, `vat`, `step_size`, `start_time`, `end_time`, `days_of_week`, `start_date`, `end_date`, `min_power_w`, `max_power_w`
- [ ] **`connectors.pricing_kind`** — `energy` · `time` · `flat` · `free` · `unknown`. Resolves the four facts `price_per_kwh IS NULL` currently conflates
- [ ] **`connectors.current_price_per_kwh`** — nullable, resolved for *now* from the bands and the connector's own `max_electric_power`; null unless `pricing_kind = 'energy'`
- [ ] **Drop `tariffs.price_per_kwh`**, and move `points.py`'s filter and `min()` to the connector column
- [ ] The resolver is a pure function over bands — tightest matching `max_power_w` wins — with tests over the nine-element tariff above, since it exercises time and power together
- [ ] Recompute `current_price_per_kwh` on the hourly tick, and after the drain
- [ ] Backfill migration for the 2,126 stored tariffs; assert the counts above are reproduced (7,175 connectors time-varying, 1,152 free)

## Slice 6 — Use the model

**Acceptance:** the map filter, the point detail and the simulator all answer with the price that actually applies, and free chargers say so.

- [ ] Map filter by **price now**, not by a minimum: `pricing_kind = 'free' OR current_price_per_kwh <= :max`. Without the `OR`, a price filter silently hides all 1,152 free chargers
- [ ] Point detail shows the band the driver is in, and that the price changes later — the difference between 0.25 and 0.47 is the app's whole argument
- [ ] **Free chargers labelled *gratis*** rather than "no price"
- [ ] Time- and session-priced connectors say how they are priced instead of showing nothing
- [ ] The simulator prices the actual charging window from the bands, spanning them where a charge crosses a boundary
- [ ] `just gen-api` — the response models change

## Slice 7 — Cadence and observation

**Acceptance:** both jobs run on a cadence that was chosen, and the phase's numbers are recorded.

- [ ] Choose the cadence per job and record why in [backend/crontab](../../backend/crontab). REE publishes the next day's PVPC once each evening, so hourly is ~23 wasted runs a day; the tariff refresh after the drain is asking about one hour of a ~7/hour change rate
- [ ] Both jobs observed running unattended for a day, with `last_error` empty
- [ ] The measured price-model numbers written into the memoria — see below

## For the memoria

- **A national registry whose change-feed could not serve a window wider than a few hours**, and which recovered without announcement. Two measurements, six weeks apart, both in [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).
- **Two thirds of sampled connectors price by time of day**, spanning nearly 2× on one tariff, and price by connector power as well. This is what justifies a charging optimiser existing at a public point rather than only at a domestic one.
- **1,152 free connectors** in the registry — a finding about the Spanish network, not about this app.
- **Real-time availability is arithmetically impossible at 5 requests/hour.** `/evses/operational_status` exists and takes `date_from`, so the data is there; 42,088 EVSEs ÷ 100 per page ÷ 5 per hour is **3.5 days for one sweep**, and per-EVSE lookups are worse. Availability therefore comes from the app's own bookings and sessions, and the honest account is that a real deployment solves this with CPO agreements or a purpose-built feed. This corrects [be-0002](../decisions/be-0002-availability-not-modelled.md), which records the *absence of data* as the reason — the budget is the real one, and the stronger argument.

## Open questions

- **Does the frozen catalogue stay frozen?** `/cpos` and `/locations` have not moved since June and drift a day every day. Right under a laptop's budget; after the drain the ordinary tick needs a few calls a day, so a weekly catalogue pass may now fit. Decide once [Slice 7](#slice-7--cadence-and-observation) has a real call-usage figure.
- **Does `tariff_elements` need `min_duration` / `max_duration`?** One and four occurrences in 200 connectors. Store them and let the resolver ignore them, or leave them in `raw_data`.

## Out of scope

- **Recovering tariff history.** No call shape returns it, and nothing in the app reads it.
- **Re-seeding the catalogue.** ~12 days under the rate cap; recovery is always a dump restore ([operations.md](../operations.md)).
- **Mirroring EVSE status.** See the memoria note above.

## Risks

- **The drain stalls on a 504 partway through.** No longer destructive — the watermark holds and `failing_since` shows how long. Resume by re-probing with `curl` and waiting for REVE.
- **The 0.7 % skip.** Accepted and quantified above; the remedy if it ever matters is one unfiltered drain.
- **`current_price_per_kwh` goes stale between recomputes.** It is a denormalisation of a band that changes on the hour, recomputed hourly. The simulator reads the bands directly and does not depend on it.
