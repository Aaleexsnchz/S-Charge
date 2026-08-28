---
id: infra-0004
status: accepted
phase: 5
date: 2026-08
related: [infra-0002, infra-0003]
---

# infra-0004: Renovate over Dependabot for dependency updates

**Decision.** Dependency updates come from the **Renovate GitHub App**, configured by [`renovate.json`](../../renovate.json) at the repository root: one grouped pull request per area on Monday mornings, majors on their own, container images pinned by digest, and **no automerge**. Security updates ignore the schedule and the approval gate. Every update is a pull request against the same four required checks as any other change, and reaches production with the next tag ([infra-0003](infra-0003-deploy-on-tag.md)).

**Rationale.** The backend is `pyproject.toml` plus `uv.lock`, and **Dependabot has no `uv` ecosystem** — its Python support is `pip`, `pipenv`, `pip-compile` and `poetry`. Choosing it would have left the entire backend dependency tree unwatched while reporting healthy coverage of the frontend, the images and the workflows, which is worse than no bot at all.

The second reason is the one this repository actually feels. Versions here are pinned in more than one file by necessity: uv appears as a CI action input and again as the binary copied into the backend image, Node appears in `frontend/.nvmrc`, in the frontend image and in `@types/node`. Renovate's custom managers read a `# renovate:` annotation and move both halves in a single pull request; Dependabot has no equivalent, so exactly the drift Phase 5 kept finding by hand — a deprecated Node runtime twice, pnpm 10 against pnpm 11, uv pinned differently in CI and in the Dockerfile, nginx four minors stale — is the class of problem it cannot see.

Grouping decides the rest. A solo project cannot absorb one pull request per package: Dependabot groups within an ecosystem, so a quiet week still arrives as four. Renovate groups across managers, so a quiet week is one pull request per area and an interesting week is a major on its own, which is the only kind worth reading carefully.

**Consequences.**

- **A third-party app holds write access to the repository.** It opens branches and pull requests; `main` stays protected, so the blast radius is a pull request that CI judges like any other. The configuration is a reviewed file in the repository rather than settings in a web console.
- **Base images are pinned by digest**, so a rebuild on the VPS can no longer silently change the patch version of Postgres, Caddy, nginx or Python. The cost is paid up front: `backend/Dockerfile` no longer templates its tag through `ARG PYTHON_VERSION`, because a digest cannot be written onto a templated tag.
- **A custom manager maintains a digest but cannot introduce one.** The betterleaks image pinned inside a workflow `run:` had its first digest resolved by hand; Renovate keeps it current from there. Any future annotated image pin inherits the same one-time step.
- **`.github/workflows/ci.yml` carries `# renovate:` annotations.** They are machine-readable directives, not commentary, and deleting one silently stops that pin being tracked.
- **Nothing opens without approval** while `dependencyDashboardApproval` is set: the dashboard issue lists everything pending and a checkbox releases each pull request. Removing that one line makes the bot autonomous, and that is the intended end state once the thesis is delivered.
- **No automerge**, so a dependency bump is a deliberate merge, consistent with [infra-0002](infra-0002-manual-release-tagging.md) and [infra-0003](infra-0003-deploy-on-tag.md): merging changes nothing in production, tagging does.
- Being current is not the same as being safe. Renovate raises what is *newer*; knowing whether a dependency is *vulnerable today* still depends on GitHub's alerts feeding it, and neither is a substitute for the scanning [production-readiness.md](../production-readiness.md) records as missing.

**Rejected alternatives.**

- *Dependabot.* Native to GitHub, zero installation, no third-party access, and the default answer for a repository this size. Rejected on the `uv` gap alone; the absence of custom managers and of cross-ecosystem grouping would each have been enough on their own. It is still not entirely absent: **its alerts are enabled and Renovate reads them** to decide what counts as a security update.
- *Self-hosted Renovate as a scheduled workflow with a personal access token.* Removes the third-party app in exchange for a long-lived token in repository secrets, a workflow to maintain and a runner minute budget. A worse trade for a personal repository — the token is the larger exposure, not the app.
- *Keep updating by hand.* What Phase 5 did, and it worked in the sense that the drift was eventually found. It was found by tripping over it, though, and always late.
- *Automerge non-majors once CI is green.* Attractive, and defensible given the pipeline. Rejected because the point of [infra-0003](infra-0003-deploy-on-tag.md) is that reaching users is a deliberate act, and a chain that ends in an unread merge weakens the claim that every change was reviewed — a claim the thesis makes.

**References.** [Dependabot's supported ecosystems](https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories) · [Renovate's pep621 manager, including uv](https://docs.renovatebot.com/modules/manager/pep621/) · [custom managers](https://docs.renovatebot.com/modules/manager/regex/)
