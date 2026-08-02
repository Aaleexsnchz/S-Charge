---
id: infra-0003
status: accepted
phase: 5
date: 2026-08
related: [infra-0001, infra-0002]
---

# infra-0003: Deploy on a tag push, not on every merge to `main`

**Decision.** Production is deployed by **pushing a tag** — any tag matching `v*`, so a patch (`v0.1.1`) ships exactly the way a minor (`v0.2.0`) does. Merging to `main` builds and tests, and nothing else. A **manual run** of the CD workflow deploys the default branch on demand, for looking at unreleased work on a real device.

`main` must still be deployable at every commit. What changes is *when* it ships, not what may be merged: partial work belongs on a branch or behind an unrouted screen, never on an untagged `main`.

**Rationale.** Shipping becomes a deliberate act, which is what [infra-0002](infra-0002-manual-release-tagging.md) already claimed about versions but the pipeline contradicted — tags were chosen by hand while every merge went to production regardless. A tag push is now the single moment a change reaches users, so several merges can accumulate behind one release and a half-built feature is not visible because it happens to be merged.

Two consequences fall out for free. Production always reports a clean `v0.2.0` rather than `v0.1.0-7-g3f2a91c`, which is the version a reader of the thesis is shown. And a documentation-only merge no longer rebuilds and recreates every container — under deploy-on-merge it did, because `git describe` changes on every commit, so the images changed on every commit too.

The demo window is the case that decides it. Under deploy-on-merge, any merge alters the live site, including the night before the defense. Under deploy-on-tag, production changes only when asked.

**Consequences.**

- **Production can lag `main`.** That is the point, but it means "merged" no longer implies "live", and forgetting to tag is now a failure mode. `/api/health` reporting `v0.1.0-7-g3f2a91c` is the tell that a manual run deployed unreleased work.
- **Shipping a fix means cutting a patch release.** Under deploy-on-merge a fix went out by merging it; now it reaches production as `v0.1.1`. Patch tags are therefore the ordinary cadence between phases, not an exception — [infra-0002](infra-0002-manual-release-tagging.md)'s bump rules already allow for this, and this record is what makes them load-bearing. A fix that is genuinely urgent and a tag that is genuinely cheap are a good pairing; the alternative, deploying unreleased `main` by hand, exists but leaves production on a version no release points at.
- **The server sits on a detached HEAD**, tracking the deployed ref rather than a moving branch. `git pull` is no longer part of a deploy; CD does `git checkout --detach`.
- **A tag deploys without re-running CI.** The commit is already on `main` and CI passed when it merged, so the tree is proven — but only under the rule that **tags point at commits already on `main`**. Tagging an arbitrary commit would deploy something CI never saw.
- Rollback is unchanged and becomes more natural: deploying is a checkout of a ref, so rolling back is the same operation aimed at the previous tag.
- [plan.md](../plan.md)'s Phase 5 criterion "deploy on merge to `main`" is superseded by this record.

**Rejected alternatives.**

- *Deploy on every merge to `main`* — what was built first, and what `plan.md` originally specified. It keeps `main` and production identical and gives the fastest feedback, which is genuinely valuable during the frontend migration where each converted screen wants checking on a phone. Rejected because that benefit is recovered by the manual run, while the costs are not recoverable the other way: no way to batch a feature across merges, production moving under a demo, and every docs merge recreating every container. A path filter would have fixed only the last of the three.
- *Deploy on merge, with a docs-only skip.* Fixes the symptom that prompted the question and none of the rest. Also adds a rule about which paths count as "not code" that has to stay correct as the repository grows.
- *Manual dispatch only, no tag trigger.* Maximum control, but then the release tag and the deployment are two separate acts that can disagree — exactly the drift this record removes.
- *Staging on merge, production on tag.* The full answer, and the right one with real users. It needs a second environment; this project has one 2 vCPU VPS and one user ([infra-0001](infra-0001-deployment.md)).
