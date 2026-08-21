# S-Charge project memory

Master's thesis (IoT): a PWA for managing EV charging. Solo developer project.

This file holds the rules that are **not discoverable by reading the code**. Anything a human would look up — how to run the stack, service URLs, the directory tree, command lists — lives in [README.md](README.md) and the [justfile](justfile) (`just --list`). Don't restate them here; they drift.

In dev only **Postgres** is containerised; the backend and frontend run natively (`just api`, `just web`). Production runs the whole stack in containers.

## Source of truth

Read before proposing architectural or scope changes:

- **[docs/README.md](docs/README.md)** — documentation index; the map of every doc. Start here to locate anything.
- **[docs/plan.md](docs/plan.md)** — the project definition: scope, architecture, phases, acceptance criteria.
- **[docs/features/](docs/features/)** — one document per feature: what it does, what exists today, what is pending.
- **[docs/phases/](docs/phases/)** — the slice plan for the phase in progress.
- **[docs/decisions/](docs/decisions/)** — ADRs. Foundational givens live in [docs/tech-stack.md](docs/tech-stack.md) instead.
- **[docs/thesis/](docs/thesis/)** — concept-level chapters for the thesis writeup, including [skills.md](docs/thesis/skills.md), the record of which agent skills this project uses.
- **[docs/operations.md](docs/operations.md)** — deploying, the production stack, database backups and restores, major Postgres upgrades.

## Working style

- **Mobile-first**, 360px reference width. The user is standing next to a charging point holding a phone.
- **UI copy is Spanish.** Code, comments, commits and docs are English.
- Slice = one pull request. Task = one commit.

## Git workflow

- **This project is personal, never the work account.** `gh` must run as `Aaleexsnchz` and commits carry the personal identity set in `.git/config` — the global `~/.gitconfig` is the work one.
- **`main` is protected and is what production runs.** Every change reaches it through a pull request; no direct commits, no force-pushes. It must stay deployable at every commit.
- **The pre-push hook is `just ci`** — both run [lefthook.yml](lefthook.yml)'s `pre-push` jobs, which mirror CI. A commit only lints and formats its staged files, so `basedpyright` and the test suites first speak at push time.
- **Never `--no-verify`.** The hooks are the gate. No secrets or credentials in the diff — the commit-time secret scan is best-effort (it needs `betterleaks` on `PATH`), and the authoritative one is a CI job over the full history.
- Branch naming, commit types and scopes, and the doc-update checklist: **[CONTRIBUTING.md](CONTRIBUTING.md)** — read it when you finish a change.

## Releases

Semantic versioning, tagged **manually**; a minor marks a phase shipping and **`v1.0.0` is the build presented for the thesis**. **The version comes from the git tag** — never hand-edit version strings in `backend/pyproject.toml` or `frontend/package.json`, they are not the source of truth. Bump rules, the tagging commands and the rationale: [docs/decisions/infra-0002](docs/decisions/infra-0002-manual-release-tagging.md).

## Backend conventions

- **Routers stay thin**: parse input, call a service, return. Business logic lives in `app/services/` and must not import FastAPI.
- One file per aggregate in `app/models/`; Pydantic request/response models in `app/schemas/`; external HTTP clients in `app/integrations/`.
- **`backend/scripts/`** is Python, run from `backend/` with `uv run python -m scripts.X`. **Repo-root `scripts/`** is bash, host-level ops (DB backup) — see [docs/operations.md](docs/operations.md).
- **Alembic: always autogenerate then review.** Never trust the diff blindly, never edit an applied migration — add a new one.
- **Tests** mirror `app/`. Service tests are unit tests with no DB; route tests use a transactional fixture or the test database.
- Ruff, `ruff format` and `basedpyright` must all pass. Type checking is push-gated, not commit-gated.

## Frontend conventions

- **Feature-first**: a file lives with the feature that owns it. `components/` and `lib/` hold only what is shared across features; a feature-specific component never goes there.
- Features stay **flat** until they grow — add a `components/`/`hooks/` subfolder inside a feature only when the first file needs it. Don't pre-create empty buckets.
- **No barrel files.** No per-feature `index.ts`, and **icons are imported per path**, never from a barrel — both defeat tree-shaking. Biome's `noRestrictedImports` enforces the icon rule for `@mui/icons-material`.
- Cross-folder imports use the `@/` alias (`@/* → src/*`); same-folder imports stay relative (`./`).
- **API types are generated**, never hand-written. **`just gen-api`** exports the schema to the committed root `openapi.json` and regenerates `lib/api/schema.d.ts` from it — run it after any change to a router or a response model, and commit both files. CI fails if either is stale, so a contract change breaks the build rather than production.
- **The frontend ships on MUI + Emotion and React Router.** Replacing them with Tailwind + shadcn/ui and TanStack Router + Form was proposed and cancelled, so do not write UI against that stack. Check [docs/tech-stack.md](docs/tech-stack.md) for what is actually installed before writing UI code.

## Documentation discipline

**Docs state current reality only.** No dated revision blocks, no "this used to be X" prose, no justifying a change inside the document it changed. When something is superseded, rewrite it and let git hold the history.

Two exceptions, both deliberate: [docs/decisions/](docs/decisions/) keeps a trail by supersession, and [docs/thesis/](docs/thesis/) may narrate an abandoned approach as a *camino no tomado* — what it promised, why it was dropped, what replaced it. Academic honesty about roads not taken is thesis content, not clutter; keep it short and keep it factual.

**Thesis chapters are written in Spanish** ([docs/thesis/](docs/thesis/)), keeping established technical terms in English (bearer token, upsert, rate limit).

**What reaches a thesis chapter, and when.** The trigger is a **concept, not a unit of work** — neither "every slice" nor "only at phase close". Most slices produce nothing for the thesis: toolchain pins, CI hygiene and version bumps are a [tech-stack.md](docs/tech-stack.md) row at most. Write when a cross-cutting system lands or a decision acquires a road not taken, and sweep once more when a phase closes, since that is when phase-plan knowledge gets migrated out anyway.

The filter: **would this still interest someone who will never read this repository?** In scope — a decision and why the alternative lost; a constraint that shaped the design (REVE's 5 req/hr cap shaped the entire ETL); a measurement (the servable refresh window, the 12-day seed cost); a threat model; a *camino no tomado*. Out of scope — tool versions and config keys, slice and PR numbers, dates and sequence ("then we did X"), and anything a reader could learn by reading the code. **A chapter that reads like a changelog has failed the test**; write the idea, and let git hold the history.

**Which documents to update when a slice ships** is a checklist applied at the end of a change, not while writing: [CONTRIBUTING.md](CONTRIBUTING.md).

**Phase plans** are written just before a phase starts, never in advance, and stay live for its duration: [docs/phases/README.md](docs/phases/README.md).

**Use the `documentation-and-adrs` skill for documentation work.** Only the deltas are recorded here and in [docs/decisions/README.md](docs/decisions/README.md) — anything the skill already says is not repeated:

- **Foundational givens get no ADR.** The skill sends every framework and library choice to a record; here a choice with no alternative ever weighed against it (Python, FastAPI, React) is a [tech-stack.md](docs/tech-stack.md) row and a paragraph in the thesis, because a record written after the fact would invent a deliberation that never happened. The full test is in [docs/decisions/README.md](docs/decisions/README.md).
- **Ids are area-prefixed** (`auth-`, `be-`, `fe-`, `infra-`), not globally sequential.
- **No `CHANGELOG.md`.** Release notes come from merged PR titles ([infra-0002](docs/decisions/infra-0002-manual-release-tagging.md)).

**Phase plans are disposable.** [docs/phases/](docs/phases/) holds working plans for the phase being built — they are not documentation, nobody reads them afterwards, and duplication between a phase plan and the permanent docs is fine. What is not fine is knowledge that exists *only* in one. **When a phase closes, migrate its permanent knowledge out first** — a decision to [docs/decisions/](docs/decisions/), an operational procedure to [docs/operations.md](docs/operations.md), a measured baseline to the feature doc that will be compared against it, a concept to [docs/thesis/](docs/thesis/). No permanent document may cite a phase plan as its source of truth.

**Skills.** When you use an agent skill on this project and it is **not already listed** in [docs/thesis/skills.md](docs/thesis/skills.md), add it there in the same change — one row, saying what it was used for *here*, not what the skill is in general. Only skills actually used on this project go in the file: the environment offers others from unrelated work, and listing those would misrepresent how this was built. The file is thesis material, so an undocumented skill is a gap in the methodology annex, not a tooling detail.
