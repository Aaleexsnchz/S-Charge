# Phase 3 — ACN import + Analytics

Per [PLAN.md](../PLAN.md): ETL pipeline for ACN-Data (Caltech's Adaptive Charging Network session dataset), aggregation endpoints, charts dashboard. ACN is bulk-imported once (no rate cap comparable to REVE), so the ETL is a resumable one-shot script, not a cron tick. API access needs a free token from <https://ev.caltech.edu/dataset> (`ACN_API_TOKEN` in `backend/.env`).

## Slice 1 — ACN ingest: client + schema + import script

**Acceptance:** with `ACN_API_TOKEN` set, `python -m scripts.import_acn --site caltech` pages through the ACN sessions API (python-eve style: `_items` + `_meta`), idempotently upserts into `acn_sessions` (keyed on the ACN `_id`), commits per page, and resumes from `--start-page` after an interruption. Row counts per site are printed at the end and recorded in the data validation doc (slice 4).

- [ ] `AcnClient` async API client (HTTP Basic, token as username) with pagination support
- [ ] `acn_sessions` model + Alembic migration (session times, energy, user inputs, raw payload)
- [ ] Idempotent `import_acn_sessions` ETL with `(rows, last_page, exhausted)` return shape
- [ ] `import_acn.py` script: per-site loop, per-page commit, `--site` / `--start-page` / `--max-pages`
- [ ] Tests: client pagination + auth, ETL upsert/idempotency/datetime+userInputs parsing

## Slice 2 — Statistics endpoints

**Acceptance:** `/api/stats/*` endpoints return aggregations computed in SQL over `acn_sessions`, fast enough for dashboard use, covered by route tests with fixture sessions.

- [ ] `GET /api/stats/overview` — totals: sessions, energy delivered, avg energy/session, avg duration, per-site breakdown
- [ ] `GET /api/stats/energy-monthly` — monthly kWh series (optionally per site)
- [ ] `GET /api/stats/arrivals-heatmap` — session arrivals by weekday × hour (site-local time)
- [ ] Route tests with fixture sessions (happy path + empty DB)

## Slice 3 — Charts dashboard

**Acceptance:** `/statistics` lazy route renders the key analytics views (overview cards, monthly energy chart, arrivals heatmap, site comparison) from the stats endpoints, in Spanish, mobile-first.

- [ ] Charting library chosen; `fe-NNNN` ADR written
- [ ] `/statistics` lazy route with overview cards + charts wired to `/api/stats/*` via TanStack Query
- [ ] Loading / error / empty states for every chart

## Slice 4 — Data validation doc

**Acceptance:** a short doc records row counts vs the source, null/gap analysis (missing `doneChargingTime`, zero-kWh sessions, userInputs coverage), and value ranges, so the thesis can state data quality honestly.

- [ ] `docs/thesis/acn-data.md` (Spanish) with counts, nulls, ranges, and import decisions
