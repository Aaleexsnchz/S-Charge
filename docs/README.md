# Documentation index

Everything under `docs/` lives here, grouped by purpose. This is the single source of truth for the doc list — the root [README](../README.md) links here rather than duplicating it.

The grouping follows [Diátaxis](https://diataxis.fr/): docs are sorted by what the reader needs — to *do* a task (how-to), *look up* a fact (reference), or *understand* a decision (explanation) — plus a project-management group for planning docs.

## How-to guides

Task-oriented, step-by-step.

| Doc | Covers |
| --- | --- |
| [setup/google-oauth.md](setup/google-oauth.md) | Enable Google sign-in: Cloud Console client, People API, the env-snapshot gotcha. |
| [setup/email.md](setup/email.md) | Wire up Resend for verification/reset email; sandbox sender limits; production DNS. |
| [DOCKER.md](DOCKER.md) | When to rebuild vs. recreate vs. do nothing after a change; database backup & restore. |

## Reference

Information-oriented; look up a fact.

| Doc | Covers |
| --- | --- |
| [reve-api-spec.json](reve-api-spec.json) | REVE external API v1 OpenAPI spec (the seed source). |

The live backend API reference is the OpenAPI/Swagger UI at <http://localhost:8000/docs>.

## Explanation

Understanding-oriented; the *why* behind the design.

### Architectural decision records

Append-only [MADR](https://adr.github.io/madr/)-style records. Full catalogue and authoring rules: [decisions/README.md](decisions/README.md).

| ID | Title |
| --- | --- |
| [auth-0001](decisions/auth-0001-fastapi-users.md) | Use `fastapi-users` as the authentication library |
| [auth-0002](decisions/auth-0002-cookie-session.md) | Single HttpOnly cookie session, no refresh tokens |
| [auth-0003](decisions/auth-0003-preregistration-shell-mitigation.md) | Pre-registration shell attack mitigation |
| [fe-0001](decisions/fe-0001-mui.md) | MUI (Material UI) as the component library |
| [fe-0002](decisions/fe-0002-pwa.md) | Ship the frontend as an installable PWA |
| [fe-0003](decisions/fe-0003-maplibre-openfreemap.md) | MapLibre GL JS + OpenFreeMap vector tiles |
| [fe-0004](decisions/fe-0004-tanstack-query.md) | TanStack Query for server state |
| [fe-0005](decisions/fe-0005-mui-x-charts.md) | MUI X Charts for in-app charts |
| [fe-0006](decisions/fe-0006-biome.md) | Biome for frontend linting and formatting |

### Thesis chapters

Concept-level write-ups (in Spanish) that feed the thesis document; each links out to the ADRs for deep rationale.

| Chapter | Covers |
| --- | --- |
| [thesis/indice.md](thesis/indice.md) | Thesis structure: chapter outline + the core idea of each chapter (the "memoria" table of contents). |
| [thesis/autenticacion.md](thesis/autenticacion.md) | Identity, password storage, session, OAuth, verification, audit, rate limiting. |
| [thesis/modelo-de-datos.md](thesis/modelo-de-datos.md) | The OCPI 2.2.1 hierarchy (CPO → Charging Point → EVSE → Connector) mirrored from REVE, and why we own the catalogue. |
| [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md) | Pricing (stored tariff → PVPC + margin) and catalogue-freshness strategy. |
| [thesis/planificacion-de-siembra.md](thesis/planificacion-de-siembra.md) | Why cron, the per-tick contract, bootstrap → steady state, the WSL2 idle caveat. |
| [thesis/robo-de-sesion.md](thesis/robo-de-sesion.md) | Threat model for infostealer + cookie replay; what an app can and cannot defend. |

## Project management

Planning and status; not part of the Diátaxis taxonomy.

| Doc | Covers |
| --- | --- |
| [PLAN.md](PLAN.md) | Scope, phases, acceptance criteria, estimates. Living doc. |
| [phases/](phases/) | Per-phase task plans ([1](phases/phase-1.md) · [2](phases/phase-2.md) · [4](phases/phase-4.md); Phase 3 dropped). Frozen once a phase ships. |
| [ideas-backlog.md](ideas-backlog.md) | Deferred ideas (AI/agent features, real payments, route optimisation) parked for the "decide later" moment. |
| [NEXT-STEPS.md](NEXT-STEPS.md) | Working handoff — where to start next session. |

## Maintenance

Documentation discipline (which docs to update when a slice ships; which are append-only) lives in the root [CLAUDE.md](../CLAUDE.md). When you add a doc, add a row here in the same commit — this index is the one place the list is maintained.
