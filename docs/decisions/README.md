# Architectural Decision Records

Records for the choices that shape what this codebase can do. Format is a lightweight [MADR](https://adr.github.io/madr/) variant: front-matter, then Decision · Rationale · Consequences · Rejected alternatives · References.

The `documentation-and-adrs` skill governs when and how to write these. This file records only where **this project differs from it**; everything the skill already covers is not repeated here.

## The one exclusion: foundational givens

The skill sends every framework, library and major dependency to a record. Here there is one carve-out, and it needs a test to apply: **can you name the road not taken, and why it lost?**

If you can — `fastapi-users` over building from primitives, mirroring REVE over proxying it, Tailwind over staying on MUI — write the record.

If the honest answer is "it is what I know" or "it is the obvious default", there was no fork. Python, FastAPI and React are in that category: foundational, but nothing was ever weighed against them. A record written after the fact would invent a deliberation that never happened, and the thesis would then rest on a fabricated rationale. Those are a [tech-stack.md](../tech-stack.md) row plus narrative justification in the thesis.

Note this only excuses *givens*, not casual choices: a dependency you would have to rip out of every file is an architectural commitment however lightly it was picked — [fe-0001](fe-0001-mui.md) is the proof, since replacing MUI costs an entire phase.

## Local convention

- **Ids are area-prefixed**, not globally sequential: `auth-`, `be-` (backend, non-auth), `fe-` (frontend), `infra-`. The area is readable without opening the file. Numbers are never reused, including after a supersession.
- **Sections:** Decision · Rationale · Consequences · Rejected alternatives · References, with `Implementation` where the rollout detail is worth keeping. Front-matter carries `id`, `status`, `phase`, `date`, and `related` / `supersedes` / `superseded_by`.
- **Statuses:** `proposed` — decided, not yet implemented. `accepted` — implemented and in force. `superseded` — replaced; add `superseded_by:` and a banner at the top.
- **Thesis chapters may narrate abandoned approaches** as a *camino no tomado*; that is content there, not clutter.

## Auth

| ID | Title | Phase |
| --- | --- | --- |
| [auth-0001](auth-0001-fastapi-users.md) | Use `fastapi-users` as the authentication library | 1 |
| [auth-0002](auth-0002-cookie-session.md) | Single HttpOnly cookie session, no refresh tokens | 1 |
| [auth-0003](auth-0003-preregistration-shell-mitigation.md) | Pre-registration shell attack mitigation | 1 |

Concept-level summary: [thesis/autenticacion.md](../thesis/autenticacion.md).

## Backend

| ID | Title | Phase |
| --- | --- | --- |
| [be-0001](be-0001-reve-mirror-not-proxy.md) | Mirror the REVE catalogue into Postgres instead of proxying it | 2 |
| [be-0002](be-0002-availability-not-modelled.md) | Do not model live availability — show points as available and say so | 3 |

## Frontend

| ID | Title | Phase | Status |
| --- | --- | --- | --- |
| [fe-0001](fe-0001-mui.md) | MUI as the frontend component library | 1 | superseded by fe-0007 |
| [fe-0002](fe-0002-pwa.md) | Ship the frontend as an installable PWA | 1 | accepted |
| [fe-0003](fe-0003-maplibre-openfreemap.md) | MapLibre GL JS + OpenFreeMap vector tiles | 2 | accepted |
| [fe-0004](fe-0004-tanstack-query.md) | TanStack Query for server state | 2 | accepted |
| [fe-0006](fe-0006-biome.md) | Biome for linting and formatting | 3 | accepted |
| [fe-0007](fe-0007-frontend-stack-migration.md) | Migrate to Tailwind + shadcn/ui and TanStack Router + Form | 6 | proposed |

`fe-0005` was MUI X Charts and stays retired: nothing renders a chart on real data yet, and the choice constrained nothing beyond one component's API — its replacement is covered by fe-0007. Restore it from git history if that judgement turns out to be wrong; the number is not reused either way.

## Infrastructure

| ID | Title | Phase |
| --- | --- | --- |
| [infra-0001](infra-0001-deployment.md) | Deploy the Docker Compose stack on a single small VPS behind Caddy | 5 |
| [infra-0002](infra-0002-manual-release-tagging.md) | Tag releases by hand; derive the running version from the tag | 5 |
| [infra-0003](infra-0003-deploy-on-tag.md) | Deploy on a tag push, not on every merge to `main` | 5 |

## Records worth writing later

Decided in principle, but cheaper to write when the work forces the detail. Don't let these ship without a record:

- **`be-0003` — booking overlap as a database constraint.** PostgreSQL 18's temporal `PRIMARY KEY … WITHOUT OVERLAPS` moves conflict detection out of application code and removes a check-then-insert race; verified working on 18.4. Write it when Phase 9 designs the bookings schema.
- **`infra-0004` — native development environment.** Only Postgres is containerised, so one toolchain gates commits, CI and the app. Rationale currently lives in [operations.md](../operations.md) and the migration chapter; promote it if it starts being re-litigated. (Earmarked as `infra-0003` until that number was taken by the deploy trigger record; numbers are never reused, so it moves rather than the written one.)
- **A wallet/ledger record** when Phase 10 chooses between signed single-entry rows and paired double-entry movements — expensive to reverse once money-shaped data exists.

## Adding a new ADR

1. Apply the exclusion test above. If it is a given, put it in [tech-stack.md](../tech-stack.md) instead.
2. Take the next free number in the area; copy the nearest existing ADR for structure.
3. Add the row here and in [docs/README.md](../README.md).
4. Commit with the change that implements the decision, or as `docs(adr):` when recorded ahead of implementation.
