# Phase 8 — Private charging points + owner pricing

Per [plan.md](../plan.md): a user registers their own charging point, decides whether it is publicly listed, and prices it — the first data in the system REVE does not provide, and the phase that turns a catalogue into a platform. What it owns is [features/owner-points.md](../../features/owner-points.md); the price model it plugs into is [be-0003](../../decisions/be-0003-price-on-the-connector.md) and [thesis/precios-y-actualizacion.md](../../thesis/precios-y-actualizacion.md).

It deliberately does not touch what a point *earns* or what happens *at* it: no sessions, no bookings, no wallet, no revenue. Those are phases 10 and 11, and the per-point stats the mock screen promises stay unbuilt until the data behind them exists.

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | The shape of a user point | Not started | — |
| 2 | Owner endpoints | Not started | — |
| 3 | Owner pricing | Not started | — |
| 4 | Visibility on the map | Not started | — |
| 5 | The My-points screen | Not started | — |

Slices run in order; 3 and 4 both depend on 1 and 2 but not on each other. **Slice 5 is the only user-visible one** — everything before it is contract and behaviour, verified by tests. If it grows past a reviewable diff, split the create form out of the list.

## Decisions taken

- **A user point reuses the OCPI hierarchy, with exactly one EVSE and one connector.** Every reader in the system — the map aggregate, `list_points`, `get_point`, the price resolver, the simulator — walks `charging_points → evses → connectors`. A flat `user_points` table would fork all of them, and the fork would have to be maintained in every future query. A domestic wallbox is one socket, so the nesting costs one extra row each and buys the whole existing read path unchanged. Rejected: a separate table (forks every reader), and letting the owner declare several connectors (a repeating form for a case domestic charging does not have, and it multiplies the pricing question by N).

- **The NOT NULL OCPI columns are filled with declared defaults, not made nullable.** `charging_points` requires `address`, `city`, `country_code`, `time_zone`, `opening_24_7` and `source_last_updated_at`; `PointRead` publishes the first four as required and every screen renders them. Relaxing them to serve user points would change the contract for 13.6k REVE points to accommodate a handful of user ones. So a user point sets `source = 'user'`, `source_id = str(id)` — its own uuid, which keeps `uq_charging_points_source_source_id` meaningful — `country_code = 'ES'`, `time_zone = 'Europe/Madrid'`, and `source_last_updated_at` = the moment the owner last edited it, which is exactly what the column means for a source that is the owner.

- **Owner pricing is a rule on the point; the resolved number stays on the connector.** [be-0003](../../decisions/be-0003-price-on-the-connector.md) put the price on the connector because a tariff shared across connectors of different power cannot carry one correct number. That argument is untouched: what the owner sets is not a price but a *rule* — fixed €/kWh, or PVPC + margin — and the rule belongs to the offering, which is the point. The connector keeps carrying the derived number that everything already reads.

- **A PVPC-indexed price is resolved on the hourly tick, never materialised as tariff bands.** The alternative was to write 24 hourly `ENERGY` rows a day into `tariff_elements` per indexed point, so the existing resolver would price them with no new code. It loses on two counts: it stores a derived value the `electricity_prices` table already holds hour by hour, and REE restates days already published — so a materialised band would go stale silently, with nothing to detect it. Instead `pricing_mode` and `margin_per_kwh` sit on the point and the tick computes `PVPC(now) + margin`. **This graduates to `be-0005` when slice 3 lands the detail**; it is listed in [decisions/README.md](../../decisions/README.md) → Records worth writing later until then.

- **User connectors are priced by their own statement, not by a branch inside the REVE resolver.** `recompute_connector_prices` is one large CTE and the most measured piece of SQL in the project. A user point has no tariff and no bands at all, so putting it through that query means adding branches to something that works, and a mistake there would misprice the whole catalogue rather than one point. A second statement scoped to `source = 'user'` runs on the same tick and cannot touch a REVE row.

- **No price when PVPC has none.** If the curve has no row for the hour, an indexed connector resolves to `pricing_kind = unknown` and shows *precio no disponible* — it does not fall back to the last known number. Same rule [be-0003](../../decisions/be-0003-price-on-the-connector.md) applied to REVE: a connector nothing has priced must not be served like one priced at zero.

- **Deleting a point archives it.** `archived_at` exists and every read already filters on it. Phase 11 hangs sessions off points, so a hard delete would eventually take a driver's history with it; the soft delete costs nothing now and is the only version that stays correct then.

- **Ownership is not verified, and the thesis says so.** Nothing in reach proves a person owns an address or a wallbox — a real platform verifies with a utility bill, a photo, or a device handshake, and each is a project of its own. A point is therefore *declared*, and the limitation is named rather than glossed: it is what makes the money in phase 10 simulated in more than one sense.

- **The owner places the point with a map pin, not a geocoded address.** The app already ships MapLibre and geolocation, so the pin is free; a geocoder is a new external dependency, a usage policy and an attribution requirement for a field the owner can type. Address, city and postal code stay text.

- **The ETL can never touch a user point.** The seed and refresh upsert on `(source, source_id)` and only ever write `source = 'reve_seed'`, so the partitions cannot collide. Stated as an invariant with a test, because it is the kind of thing that stays true only while someone remembers it.

## Slice 1 — The shape of a user point

**Acceptance:** a service call creates a user point with its EVSE and connector, and `GET /api/points/{id}` serves it through the unchanged read path.

- [ ] Migration: `visibility` (`public` | `private`, NOT NULL, `server_default 'public'` so the 13.6k REVE rows are correct without a backfill), `pricing_mode` (`fixed` | `pvpc_plus_margin`, nullable — REVE points have no owner rule), `fixed_price_per_kwh` and `margin_per_kwh` (`Numeric(8, 4)`, nullable) on `charging_points`. Autogenerate, then read the diff: the enums are new types and Alembic's autogenerate does not always order `CREATE TYPE` before the column that uses it
- [ ] Model fields and the `ChargingPointVisibility` / `OwnerPricingMode` enums, following `ChargingPointSource`'s `values_callable` spelling so the stored values stay the lowercase strings
- [ ] `services/owner_points.py`: create a point with its single EVSE and connector in one transaction, filling the declared defaults. Unit-tested with no DB where the shape allows, and against the test database for the constraint behaviour
- [ ] A test asserting the ETL invariant: a refresh tick over a database containing a user point leaves it byte-identical

## Slice 2 — Owner endpoints

**Acceptance:** an authenticated user can create, list, edit and archive their own points over HTTP, and cannot see or touch anyone else's.

- [ ] `GET /api/points/mine` — the caller's points, archived ones excluded
- [ ] `POST /api/points` — create; the body carries location, address, connector standard, format, power type, power, visibility and the pricing rule
- [ ] `PATCH /api/points/{id}` and `DELETE /api/points/{id}` (archive), both scoped to the owner
- [ ] **Someone else's point answers 404, not 403.** A 403 confirms the id exists, which is a disclosure the app gets nothing for; the router already returns REVE's error shape for an unknown point, so an unowned one is indistinguishable from an absent one
- [ ] Route tests on the transactional fixture: each verb against a point owned by another user, and against an archived one
- [ ] `just gen-api`, with `openapi.json` and `schema.d.ts` committed in the same commit — CI fails on a stale contract

## Slice 3 — Owner pricing

**Acceptance:** a user point priced fixed and one priced PVPC + margin both resolve a current price on the hourly tick, and the point detail shows what each costs.

- [ ] A second resolver statement for `source = 'user'` connectors, run from the same tick as `recompute_connector_prices`: `fixed` writes the number, `pvpc_plus_margin` writes `PVPC(now) + margin`, and a missing PVPC hour writes `unknown`
- [ ] `price_suggestion.py` finally gets its caller: the create form is offered the calibrated defaults (AC +0.22 / DC +0.32 €/kWh over PVPC, from ~27k real tariffs — [phase-3](phase-3.md)) as a starting margin, presented as a suggestion and overridable
- [ ] Point detail renders a user point's price: the fixed number, or the PVPC curve plus the owner's margin — the prices screen already draws that curve, so the band card should read it rather than grow a second renderer
- [ ] Service tests for both modes, including the empty-PVPC case

**Open question, to settle here:** whether the owner's number is understood as including VAT. OCPI's `price` is ex-VAT and the app does not currently say so anywhere ([open-items](open-items.md), from phase 6), but an owner typing *0,25 €/kWh* means what they would charge a neighbour, which is retail. Whatever is chosen has to be stated in the form's copy, not just in the code.

## Slice 4 — Visibility on the map

**Acceptance:** a public user point appears on the map alongside REVE's; a private one appears nowhere but its owner's My-points and its own detail page.

- [ ] `list_points` and `map_feature_collection` filter `visibility = 'public'`
- [ ] `GET /api/points/{id}` serves a private point to its owner and 404s for anyone else
- [ ] **`/points/map` stays user-independent.** Showing an owner their own private markers would make the response vary per user, and that endpoint rebuilds an aggregate over ~13.6k points and ships ~503 KB gzipped — a per-user response cannot be cached once, which is precisely the fix phase 14 has planned for it. A handful of private markers is not worth the shared cache; the owner reaches their point from Mis puntos

## Slice 5 — The My-points screen

**Acceptance:** `/my-points` lists, creates, edits and deletes real points on a 360 px screen, and `myPoints.mock.ts` is gone.

- [ ] The list on `GET /api/points/mine`, with an empty state that explains what the screen is for — it is what every new user sees, and it is the app's only invitation to contribute a point
- [ ] The create form: map pin with the user's position as the default centre, address fields, connector standard / format / power type / power, the visibility toggle, and the pricing rule with its suggested margin
- [ ] Edit and delete, delete behind a confirmation
- [ ] Delete `myPoints.mock.ts`, the `PlaceholderBadge` on the page, and the FAB's *próximamente* snackbar; drop the fixture's row from [features/README.md](../../features/README.md)
- [ ] The per-point stats the mock invented (`bookingsThisMonth`, `earningsEur`) **do not come back as zeroes** — a zero is a claim that nothing happened, when the truth is that nothing is measured yet. They return with sessions in phase 11

## Open questions

- **What happens to a user's points when the account is deleted.** `owner_user_id` is `ON DELETE SET NULL`, which for a REVE point is right and for a user point leaves a public charging point nobody owns and nobody can edit. Archiving the point with the account is the likely answer, but erasure is not built and its shape is part of the GDPR work in the [public-launch gate](../plan.md#opening-to-the-public) — decided there, not guessed here.
- **Whether an owner should see their own private points on the map.** Decided *no* in slice 4 for a cacheability reason that is about `/points/map` specifically. If phase 9's optimiser wants the map as its entry point to an owned point, that reopens — and the answer then is probably a separate thin endpoint, not a per-user aggregate.

## Out of scope

Sessions, bookings and anything that happens *at* a point (phase 11); revenue and the ledger (phase 10); ownership verification; geocoding; several connectors on one point; photos; availability windows beyond the `opening_24_7` flag; and any change to how REVE points are priced.

## Risks

- **The pricing tick is shared with the catalogue.** A bug in the user-point resolver runs on the same schedule as the REVE one. Mitigated by keeping them separate statements — the decision above — so the blast radius of the new one is the rows it selects.
- **The create form is the largest single piece of UI in the phase**, on the narrowest screen the app supports. If it does not fit a 360 px viewport without becoming a wizard, it is split by section rather than paginated.
