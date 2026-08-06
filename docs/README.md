# Documentation index

Everything under `docs/` lives here, grouped by purpose — the root [README](../README.md) links here rather than duplicating it. The index is two levels: this file lists the top-level docs and the folders; the per-item lists for [features/](features/) and [phases/](phases/) live in their own READMEs. Add a new doc to whichever of the two is its home, in the same commit.

The grouping follows [Diátaxis](https://diataxis.fr/): docs are sorted by what the reader needs — to *do* a task (how-to), *look up* a fact (reference), or *understand* a decision (explanation) — plus a project-management group for planning docs.

Filenames inside `docs/` are lowercase kebab-case; uppercase is reserved for the files convention expects at a repo root (`README`, `AGENTS`, `CLAUDE`, `CONTRIBUTING`).

Two project docs live at the root rather than here, because tooling and habit expect them there: [CONTRIBUTING.md](../CONTRIBUTING.md) (branch, commit and doc-update conventions — GitHub surfaces it when a PR is opened) and [AGENTS.md](../AGENTS.md) (conventions for agents working in the repo).

## How-to guides

Task-oriented, step-by-step.

| Doc | Covers |
| --- | --- |
| [setup/google-oauth.md](setup/google-oauth.md) | Enable Google sign-in: Cloud Console client, People API, the env-snapshot gotcha. |
| [setup/email.md](setup/email.md) | Wire up Resend for verification/reset email; sandbox sender limits; production DNS. |
| [setup/deployment.md](setup/deployment.md) | Provision the production VPS: hardening, DNS, env files, DB bootstrap from seed dump, CD secrets, security gate. |
| [operations.md](operations.md) | Day-2 operations: the production stack and its image stages, deploying, major Postgres upgrades, database backup & restore (local + offsite). |

## Reference

Information-oriented; look up a fact.

| Doc | Covers |
| --- | --- |
| [tech-stack.md](tech-stack.md) | Every library and tool in the project, and the reason it is there. |
| [features/](features/) | One document per feature: what it does, what exists today, what is pending. |
| [reve-api-spec.json](reve-api-spec.json) | REVE external API v1 OpenAPI spec (the seed source). |

The live backend API reference is the OpenAPI/Swagger UI at <http://localhost:8000/docs>.

## Explanation

Understanding-oriented; the *why* behind the design.

### Architectural decision records

Authoring rules, the local convention and what belongs here rather than in [tech-stack.md](tech-stack.md): [decisions/README.md](decisions/README.md).

| ID | Title |
| --- | --- |
| [auth-0001](decisions/auth-0001-fastapi-users.md) | Use `fastapi-users` as the authentication library |
| [auth-0002](decisions/auth-0002-cookie-session.md) | Single HttpOnly cookie session, no refresh tokens |
| [auth-0003](decisions/auth-0003-preregistration-shell-mitigation.md) | Pre-registration shell attack mitigation |
| [be-0001](decisions/be-0001-reve-mirror-not-proxy.md) | Mirror the REVE catalogue into Postgres instead of proxying it |
| [be-0002](decisions/be-0002-availability-not-modelled.md) | Do not model live availability — show points as available and say so |
| [fe-0001](decisions/fe-0001-mui.md) | MUI as the component library *(superseded by fe-0007)* |
| [fe-0002](decisions/fe-0002-pwa.md) | Ship the frontend as an installable PWA |
| [fe-0003](decisions/fe-0003-maplibre-openfreemap.md) | MapLibre GL JS + OpenFreeMap vector tiles |
| [fe-0004](decisions/fe-0004-tanstack-query.md) | TanStack Query for server state |
| [fe-0006](decisions/fe-0006-biome.md) | Biome for linting and formatting |
| [fe-0007](decisions/fe-0007-frontend-stack-migration.md) | Migrate to Tailwind + shadcn/ui and TanStack Router + Form |
| [infra-0001](decisions/infra-0001-deployment.md) | Deploy the Docker Compose stack on a single small VPS behind Caddy |
| [infra-0002](decisions/infra-0002-manual-release-tagging.md) | Tag releases by hand; derive the running version from the tag |
| [infra-0003](decisions/infra-0003-deploy-on-tag.md) | Deploy on a tag push, not on every merge to `main` |

### The thesis document

| Where | What |
| --- | --- |
| [thesis/memoria/](thesis/memoria/) | **The memoria itself** — the fifteen chapters that get submitted and defended, in Spanish, plus the IEEE bibliography and the appendix outline. Start at its [README](thesis/memoria/README.md). |

### Thesis chapters

Concept-level write-ups (in Spanish) that feed the memoria; each links out to the ADRs for deep rationale. These are working notes, not the submitted document.

| Chapter | Covers |
| --- | --- |
| [thesis/indice.md](thesis/indice.md) | The outline the memoria was written from. Superseded by [thesis/memoria/](thesis/memoria/) as the authoritative structure. |
| [thesis/autenticacion.md](thesis/autenticacion.md) | Identity, password storage, session, OAuth, verification, audit, rate limiting. |
| [thesis/modelo-de-datos.md](thesis/modelo-de-datos.md) | The OCPI 2.2.1 hierarchy (CPO → Charging Point → EVSE → Connector) mirrored from REVE, and why we own the catalogue. |
| [thesis/precios-y-actualizacion.md](thesis/precios-y-actualizacion.md) | Pricing (stored tariff → PVPC + margin) and catalogue-freshness strategy. |
| [thesis/simulacion-de-recarga.md](thesis/simulacion-de-recarga.md) | Pre-charge simulation: spec-based power/energy/duration model (AC flat, DC taper) and cost. |
| [thesis/migracion-del-stack.md](thesis/migracion-del-stack.md) | The mid-project stack changes as revised decisions: frontend (MUI → Tailwind + shadcn/ui + TanStack), PostgreSQL 18, Python 3.13, native dev, tooling. Alternatives and how each is verified. |
| [thesis/planificacion-de-siembra.md](thesis/planificacion-de-siembra.md) | Why cron, the per-tick contract, bootstrap → steady state, the WSL2 idle caveat. |
| [thesis/robo-de-sesion.md](thesis/robo-de-sesion.md) | Threat model for infostealer + cookie replay; what an app can and cannot defend. |
| [thesis/skills.md](thesis/skills.md) | Which agent skills the project uses and what for; how to materialise them on a fresh clone. Add a row the first time you use a new one. |

## Project management

Planning and status; not part of the Diátaxis taxonomy.

| Doc | Covers |
| --- | --- |
| [plan.md](plan.md) | The project definition: scope, architecture, phases, acceptance criteria. Living doc, current state only. |
| [phases/](phases/) | Per-phase slice plans, written just before each phase starts. Conventions and the structure a plan follows: [phases/README.md](phases/README.md). |
| [features/](features/) | Per-feature status and pending work. Also listed under Reference above. |
| [ideas-backlog.md](ideas-backlog.md) | Deferred ideas (AI/agent features, real payments, route optimisation) parked for the "decide later" moment. |
| [production-readiness.md](production-readiness.md) | Known gaps against production-grade operation: what serving real users would require that this deployment deliberately omits, and why. Not a feature backlog — a register of conscious omissions. |

## Maintenance

Which docs to update when a slice ships is in [AGENTS.md](../AGENTS.md) → Documentation discipline. In short: docs state **current reality only** — no dated revision blocks, no superseded prose left in place. Two exceptions: [decisions/](decisions/), where a reversed decision is superseded by a new ADR rather than edited away, and [thesis/](thesis/), where an abandoned approach is narrated as a *camino no tomado* because that is academic content.
