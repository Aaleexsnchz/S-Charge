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

### `price_per_kwh IS NULL` conflates four different facts

Of the 1,195 connectors on a tariff with no per-kWh price:

- 1,152 publish a zero — read at planning time as **free**
- ~43 are priced by time or session (TIME €0.17–3.85/h, FLAT €0.77)
- 1 carries `ENERGY 9110.66`, bad data at source, correctly rejected

**The "free" reading did not survive [Slice 5](#slice-5--model-the-tariff).** Against the bands as rows, 1,144 of those 1,152 are an unfilled template — a lone `FLAT 0.0`, no VAT, `step_size` 0, no energy band — and only 30 connectors are genuinely free. Separating the four facts was the right goal; the count attached to it was an artefact of the model being replaced.

### Nothing needs re-fetching to fix the model

**All 2,126 tariffs hold their complete `elements` array in `raw_data`**, including rows last refreshed on 10 June — verified, zero empty. The flattening happens on the way *out*, never on the way in. So the price model can be built and backfilled from the database with no network calls, in parallel with the drain.

Restrictions are resolvable without a session in ~99.6 % of cases: across 200 sampled connectors, `start_time`/`end_time` 1364, `day_of_week` 1165, `max_power` 1161, `start_date`/`end_date` ~200, against `min_duration` 4 and `max_duration` 1. The session-dependent handful is why the denormalised price is *"price now, absent session-dependent restrictions"* and the simulator — which knows the session — can do better.

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | Confirm the server matches the measurement | Done | host work |
| 2 | Remove the automatic watermark jump | Done | #37 |
| 3 | Advisory lock on the REVE tick | Done | #41 |
| 4 | Turn the scheduler on | Not started | host work |
| 4b | Capture the connectors REVE has and we do not | Not started | — |
| 5 | Model the tariff | Done | — |
| 6 | Use the model | Not started | — |
| 7 | Cadence and observation | Not started | host work |

**4 and 5 run in parallel.** The drain is a cron ticking for 16 hours; Slice 5 is desk work against `raw_data` and needs no network. **4b must land while 4 is still draining** — it records a signal the drain emits and discards, so every page that passes before it ships is a page whose evidence is lost. 6 depends on 5; 7 closes the phase.

## Decisions taken

- **Backfill by `date_from`, not by an unfiltered drain.** Measured: 16 h against ~4 days, for a 0.7 % skip rate. Recorded above with the arithmetic.
- **The watermark is not moved backwards to reach stale rows.** Tempting, because the 2,138 expired tariffs sit just outside the window — but `date_from` filters by *when the row last changed at source*, not by when we last saw it, and a row that has not changed cannot be re-fetched into something different. We already hold exactly what REVE publishes for them. Reaching the bulk means `date_from = 2025-12-01`, a nine-month window on an endpoint that times out on days, to re-download 2,060 byte-identical expired rows. And it is unnecessary by construction: if a CPO ever republishes one, `last_tariff_updated` moves forward and the **current** watermark catches it on the next tick. Moving it back costs budget and 504 risk for no information.
- **Let the scheduler do the drain.** It is safe now — the watermark cannot be jumped ([#37](https://github.com/Aaleexsnchz/S-Charge/pull/37)) and concurrent writers cannot corrupt the cursor ([#41](https://github.com/Aaleexsnchz/S-Charge/pull/41)) — and 5 calls/hour against ~78 pages is exactly the 16 hours needed. Draining by hand would spend the same budget with more chances to get it wrong.
- **`tariffs.price_per_kwh` is dropped, not redefined.** A tariff shared across connectors of different power cannot carry one correct price. Replaced by `connectors.current_price_per_kwh` plus `connectors.pricing_kind`.
- **Unpriced points are shown and labelled, never hidden or deleted.** A point that exists is worth showing even when its price is unknown. Matches [be-0002](../decisions/be-0002-availability-not-modelled.md)'s rule for availability — and the corollary found while building it is that a *label* must be earned too: `unknown` is the honest answer wherever the source did not actually state a price.

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
- [ ] **Count `reve_tariff_connector_not_found` in the scheduler log.** Every one is a connector REVE has and the mirror does not, so the drain measures catalogue drift for free — no extra call. This is the evidence the open question below has been waiting for:
      `docker compose -f docker-compose.prod.yml logs scheduler | grep -c reve_tariff_connector_not_found`

## Slice 4b — Capture the connectors REVE has and we do not

**Acceptance:** every tariff row for a connector outside the mirror is recorded rather than dropped, and the record is enough to fetch that EVSE later.

The catalogue is frozen at the June seed and drifts a day every day ([be-0001](../decisions/be-0001-reve-mirror-not-proxy.md) accepts this; refreshing `/locations` would starve the tariff budget). But the refresh already *meets* the evidence: `/connectors/tariffs` returns rows for connectors that were never seeded, and `_upsert_connector_tariff` logs `reve_tariff_connector_not_found` and throws the row away. A log line is not a work queue.

**The API supports repair, which is what makes this worth storing.** `/evses/{evse_id}` fetches one EVSE by exactly the id the discarded row carries, and `/locations` accepts `party_id` / `cpo_id`, so a later slice can drain the backlog one call at a time under the 5 req/hr cap instead of re-seeding for ~12 days.

- [ ] **`reve_unmirrored_connectors`** — `evse_id`, `connector_id`, unique together; `first_seen_at`, `last_seen_at`, `tariff_raw` (the payload we could not attach, so nothing is lost), `resolved_at` nullable
- [ ] `_upsert_connector_tariff` upserts here instead of only warning; the warning stays, since a sudden jump is worth seeing in the logs
- [ ] Counted in the `reve_etl_tariffs` audit line, so each tick reports how many rows landed outside the mirror
- [ ] `--status` prints the backlog size — it is the answer to *how stale is the catalogue*, which nothing currently reports
- [ ] The `evse_id` is eMI3 (`ES*ABC*E1`), so the party id is recoverable from it for a `party_id`-filtered `/locations` pass. Derive it when the backfill slice needs it, not now

**Deliberately not in this slice:** fetching the missing EVSEs. That spends REVE budget and competes with the drain, and the backlog has to exist before its size can justify a cadence. [Slice 7](#slice-7--cadence-and-observation) decides that with a real number in hand.

## Slice 5 — Model the tariff [x]

The bands are rows in `tariff_elements` and the resolved price lives on the connector. The decision and its rejected alternatives moved to [be-0003](../decisions/be-0003-price-on-the-connector.md); the measurements to [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).

The band-shape count reproduced exactly: **7,175** connectors on a tariff publishing more than one energy price. The backfill runs in ~2 s over 2,126 tariffs → 5,513 band rows, resolving to **38,548 energy · 8,197 unknown · 33 time · 30 free**.

**The plan's "1,152 free" was wrong, and finding out why is the most useful thing this slice did.** That number came from reading `price_per_kwh IS NULL` on the old flattened model. Once the bands are rows, 1,144 of those 1,152 turn out to carry a lone `FLAT 0.0` with no VAT, `step_size` 0 and **no energy band at all** — an unfilled template, not a free charger. The CPOs publishing them price the rest of their estate normally: Etecnic has 685 of these against 1,084 priced connectors, ELECTROMAPS 148 against 1,742. **30 connectors are genuinely free**, each an explicit `ENERGY 0.0` with VAT and step_size populated. Labelling the other 1,144 *gratis* would have sent drivers to chargers that bill them.

**Five things the work turned up that the plan did not anticipate:**

- **The recompute is one SQL statement, not a pure Python function.** "What does this connector cost now?" is a bulk update over ~47,000 rows; "what does this charging window cost?" is a different question, and it is the simulator's, in [Slice 6](#slice-6--use-the-model). The migration carries a frozen copy of the statement rather than importing it, so a later change to the live one cannot break `alembic upgrade head`.
- **Ends are inclusive, against the spec.** OCPI calls `end_time` and `end_date` exclusive. REVE's publishers do not: bands run `00:00–06:59` / `07:00–22:59`, and **275 of the 406 dated bands set `start_date = end_date`** for a single day — unmatchable on any date at all under an exclusive reading. Both bounds are inclusive here, and the connector power bound with them, since a session never reaches the connector's rating exactly.
- **An expired tariff was still pricing 2,138 connectors.** The resolver never read `tariffs.valid_from` / `valid_to`. These are not stale defaults: the expired tariffs average **0.1129 €/kWh against 0.3517** for the live ones, so they are ended promotions, and serving one sends a driver to a charger expecting to pay a third of the real price. 2,115 of the 2,138 were already expired when REVE served them, so this predates the stall. The window is now honoured.
- **Two ordering rules decide the price, and both were wrong at first.** Ranking candidate bands by *how many* restrictions they carry lets a band with a time window outrank a tighter power band, handing a 22 kW connector the fast-charge price; the rule only has to separate a real band from the tariff's unrestricted fallback, so it is a boolean, not a count. And `bool_and` ignores nulls, so a component with no price at all passed as a zero one and would have published an unfilled record as *free* — the exact shape this slice exists to reject. Neither shows up in today's data; both would have arrived with the drain.
- **REVE writes `0` where it means "not set", and a literal reading is destructive.** A band capped at `max_power = 0` matches no connector at all; one gated behind `min_duration = 0` is not gated, but reads as session-only. Storing the zeros verbatim left **797 connectors resolving to `unknown` that have a perfectly good price**, and a further **1,247 across 127 tariffs** took an unrestricted fallback band over the window that actually applied, because source order decided the tie. Bounds of `0` are now folded to null at ingest, and the resolver prefers the more specific band over the fallback. `raw_data` still holds the literal source.
- **A stalled ETL can leave a connector with no price rather than a stale one — and the unrestricted band is what stops it.** **1,532** connectors sit on tariffs published as a *dated* schedule: a band per quarter-hour, valid for one named day, frozen the day the watermark did. Every one of those bands has expired, and the tariff's own unrestricted fallback band is what still prices **1,485** of them. Only **47** have no fallback and resolve to `unknown`. That is the argument for keeping the fallback rather than treating it as noise, and it only became visible once the bands were rows that could be counted.

**Answered here:** `tariff_elements` stores **every** restriction the spec defines, including `min_duration` / `max_duration` and the energy and current limits. They are nullable columns on a table that exists anyway, the simulator knows the session and can use them, and leaving them in `raw_data` would have made the mirror lossy for no saving. The "price now" resolver treats a band gated behind any `min_*` as *not yet active* and ignores the `max_*` caps.

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

- **A national registry whose change-feed could not serve a window wider than a few hours**, and which recovered without announcement. Two measurements, six weeks apart, both in [precios-y-actualizacion.md](../thesis/precios-y-actualizacion.md).
- **Two thirds of sampled connectors price by time of day**, spanning nearly 2× on one tariff, and price by connector power as well. This is what justifies a charging optimiser existing at a public point rather than only at a domestic one.
- **An incremental `date_from` feed cannot repair data the source never touches.** 2,138 connectors are priced by an expired promotional tariff, and every one of those tariffs was last modified before the window the refresh asks about. No cadence, no budget and no full drain fixes them, because REVE would serve the same expired row back. The mirror's freshness is bounded by the publisher's diligence, not by the puller's effort — the argument for showing *unknown* rather than a number, and a real limit to state rather than hide.
- **A registry where a zero is usually a blank.** 1,144 connectors publish a tariff whose every field is a zero default, and reading those as *free* rather than *unfilled* would have mislabelled 38× more chargers than are actually free (30). The same `0`-for-null habit appears in the restrictions, and an expired promotional tariff keeps being served as current. The lesson generalises past this registry: **in an open data feed, a zero is a claim only when the fields around it are populated too** — a finding about data quality in public infrastructure registries, not about this app.
- **Real-time availability is arithmetically impossible at 5 requests/hour.** `/evses/operational_status` exists and takes `date_from`, so the data is there; 42,088 EVSEs ÷ 100 per page ÷ 5 per hour is **3.5 days for one sweep**, and per-EVSE lookups are worse. Availability therefore comes from the app's own bookings and sessions, and the honest account is that a real deployment solves this with CPO agreements or a purpose-built feed. This corrects [be-0002](../decisions/be-0002-availability-not-modelled.md), which records the *absence of data* as the reason — the budget is the real one, and the stronger argument.

## Open questions

- **Is `CONGESTION_TIME` worth pricing?** 218 band rows carry a component type absent from REVE's own published enum. It is a surcharge, so it never outranks `ENERGY`, `TIME` or `FLAT`; a connector whose only applicable band is one resolves to `unknown`. Revisit if the drain makes it common.
- **Does the frozen catalogue stay frozen?** `/cpos` and `/locations` have not moved since June and drift a day every day. [Slice 4b](#slice-4b--capture-the-connectors-reve-has-and-we-do-not) turns the drain's `reve_tariff_connector_not_found` count into a stored backlog, which is the free lower bound on how many connectors REVE has gained since the seed. Decide the catalogue cadence in [Slice 7](#slice-7--cadence-and-observation) against that number. Right under a laptop's budget; after the drain the ordinary tick needs a few calls a day, so a weekly catalogue pass may now fit. Decide once [Slice 7](#slice-7--cadence-and-observation) has a real call-usage figure.

## Out of scope

- **Recovering tariff history.** No call shape returns it, and nothing in the app reads it.
- **Re-seeding the catalogue.** ~12 days under the rate cap; recovery is always a dump restore ([operations.md](../operations.md)).
- **Mirroring EVSE status.** See the memoria note above.

## Risks

- **The drain stalls on a 504 partway through.** No longer destructive — the watermark holds and `failing_since` shows how long. Resume by re-probing with `curl` and waiting for REVE.
- **The 0.7 % skip.** Accepted and quantified above; the remedy if it ever matters is one unfiltered drain.
- **`current_price_per_kwh` goes stale between recomputes.** It is a denormalisation of a band that changes on the hour, recomputed hourly. The simulator reads the bands directly and does not depend on it.
