# Contributing

How a change gets from a working tree into `main`. Read this when you finish a piece of work — it is the reference applied at that moment, not while writing code.

Running the stack and the day-to-day commands are in the [README](README.md).

## Branch

Branch off `main`, one branch per slice:

```text
<type>/<scope>-<short-description>
```

`feat/backend-user-profile`, `fix/frontend-navbar-overlap`, `docs/root-adr-cleanup`.

## Commit

Conventional Commits — `<type>(<scope>): <imperative summary>`. Present tense, imperative mood ("add", not "added" or "adds"), under ~72 characters. **One logical change per commit**; no mixing unrelated changes in one commit, and no mixing unrelated concerns in one PR.

| Type | For |
| --- | --- |
| `feat` | new user-visible capability |
| `fix` | a bug |
| `docs` | documentation only |
| `style` | formatting only, no logic change |
| `refactor` | restructuring with no behaviour change |
| `perf` | measurably faster, no behaviour change |
| `test` | adding or updating tests |
| `build` | dependencies, images, task runner, dev environment |
| `ci` | workflows and pipeline config |
| `chore` | maintenance that fits nowhere else |
| `revert` | reverts a previous commit |

Scopes: **`backend`**, **`frontend`**, **`root`** (repo-wide: docs, justfile, compose), **`infra`** (deployment, CI/CD, server).

Breaking changes take the standard markers — `feat!:` or a `BREAKING CHANGE:` footer. They carry no automation here, since versions are chosen deliberately rather than derived from history ([infra-0002](docs/decisions/infra-0002-manual-release-tagging.md)), but they make the diff's blast radius legible in the log.

## Update the docs in the same commit

A change that leaves a document stale is not finished. When a slice ships, work through these:

- **[docs/features/](docs/features/)** — the feature's document: move its status, delete the mock it just replaced, update what is pending
- **[docs/plan/phases/phase-N.md](docs/plan/phases/)** — tick the task, move the slice's row in the status table, record the PR
- **[docs/plan/plan.md](docs/plan/plan.md)** — tick acceptance bullets and move the phase's status; rewrite the phase prose if shipped reality diverges. High-level only: no slice detail, no history
- **[docs/README.md](docs/README.md)** — add or adjust the index row when you add, move or remove a doc
- **[docs/tech-stack.md](docs/tech-stack.md)** — a new library or tool gets a row with one line on why it is there
- **[docs/decisions/](docs/decisions/)** — a fork in the road gets a record; the test is in [decisions/README.md](docs/decisions/README.md)
- **[docs/thesis/](docs/thesis/)** — update the matching chapter when a cross-cutting system lands (auth, ETL, simulation); write a new one if none matches. **Chapters are in Spanish**, keeping established technical terms in English (bearer token, upsert, rate limit)
- **[README.md](README.md)** — only what a contributor needs: a changed quick start, a new top-level component, a stack change. Phase and thesis status do not belong there
- **[docs/thesis/skills.md](docs/thesis/skills.md)** — if you used an agent skill not already listed

How to write those docs — current reality only, the two exceptions, phase plans being disposable — is in [AGENTS.md](AGENTS.md) → Documentation discipline, because it applies while writing, not only at the end.

## Push and open the PR

The pre-push hook runs exactly what CI runs, and CI is the merge gate; `just ci` is the same battery on demand, before you get there. Committing lints, formats and secret-scans the staged files — **never `--no-verify`**.

The whole battery is affordable in a hook because the jobs run in parallel: **~8 s of wall time against ~29 s of CPU**, so the cost is the slowest job rather than the sum. That measurement is why no check had to be dropped to make the gate fast enough to keep.

Open the PR early. `main` is protected: pull request required, CI checks required, no direct commits, no force-pushes. It is what production runs, so it must stay deployable at every commit.

Merge once CI is green. The PR title becomes the release note ([infra-0002](docs/decisions/infra-0002-manual-release-tagging.md)), so write it for a reader who was not there.
