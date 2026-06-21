# Phase 3 — ACN import + internal analysis

> **Revision 2026-06-12.** Product refocus: ACN data is internal modelling input, never user-facing content. The statistics endpoints + `/statistics` dashboard originally planned as slices 2–3 were built and then deliberately removed (commit `118bb3c` / revert `fdf9198`); their replacement is a thesis analysis notebook outside the app. Slice numbering below reflects the new shape.

Per [PLAN.md](../PLAN.md): ETL pipeline for ACN-Data (Caltech's Adaptive Charging Network session dataset) plus a thesis analysis notebook. ACN is bulk-imported once (no rate cap comparable to REVE), so the ETL is a resumable one-shot script, not a cron tick. API access needs a free token from <https://ev.caltech.edu/dataset> (`ACN_API_TOKEN` in `backend/.env`).

## Slice 1 — ACN ingest: client + schema + import script

**Acceptance:** with `ACN_API_TOKEN` set, `python -m scripts.import_acn --site caltech` pages through the ACN sessions API (python-eve style: `_items` + `_meta`), idempotently upserts into `acn_sessions` (keyed on the ACN `_id`), commits per page, and resumes from `--start-page` after an interruption. Row counts per site are printed at the end and recorded in the data validation doc (slice 3).

- [x] `AcnClient` async API client (HTTP Basic, token as username) with pagination support
- [x] `acn_sessions` model + Alembic migration (session times, energy, user inputs, raw payload)
- [x] Idempotent `import_acn_sessions` ETL with `(rows, last_page, exhausted)` return shape
- [x] `import_acn.py` script: per-site loop, per-page commit, `--site` / `--start-page` / `--max-pages`
- [x] Tests: client pagination + auth, ETL upsert/idempotency/datetime+userInputs parsing
- [ ] Real import run against the live API with `ACN_API_TOKEN` (validates the assumed eve response shape)

## Slice 2 — Analysis notebook (thesis material)

**Acceptance:** a Jupyter notebook under `analysis/` reads `acn_sessions` directly from Postgres and produces the figures + short written conclusions the thesis data chapter needs: energy distributions, monthly volumes, weekday×hour arrival heatmap, cross-site comparison, userInputs coverage. Not part of the app; not deployed.

- [ ] `analysis/acn-analysis.ipynb` with reproducible DB connection (env-driven) and the four figure groups
- [ ] Conclusions cell per figure (Spanish) reusable in the thesis

## Slice 3 — Data validation doc

**Acceptance:** a short doc records row counts vs the source, null/gap analysis (missing `doneChargingTime`, zero-kWh sessions, userInputs coverage), and value ranges, so the thesis can state data quality honestly.

- [ ] `docs/thesis/acn-data.md` (Spanish) with counts, nulls, ranges, and import decisions
