# Phase N — <name from plan.md>

<!--
Copy this file to phase-N.md when the phase starts. Delete every comment as you fill it in,
and delete any section the phase does not need — a phase with no real risks should not invent any.
-->

Per [plan.md](../plan.md): <one paragraph — what this phase builds and what "done" means for it>. <The document that owns the model or rationale behind it, linked.> <Anything the phase deliberately does not touch.>

| Slice | Scope | Status | PR |
| --- | --- | --- | --- |
| 1 | <scope> | Not started | — |
| 2 | <scope> | Not started | — |

<!--
Status values in use: Not started · In progress · Done · "Done, <what is still open>" · Moved to Phase N.
PR column: the number, or "host work" for anything done on the server, or "—".
One branch and one PR per slice. Size them so no PR becomes unreviewable.
Numbering is creation order, not running order — say so here if they differ, and say what blocks what.
-->

<!-- Once the phase is running, a short "where things stand" paragraph goes here and stays current. -->

## Decisions taken

<!--
The calls settled while planning, each with the alternative that was rejected and why.
This is the part that ends up in the thesis. A decision with a fork in the road gets an
ADR instead, and is referenced from here rather than argued twice.
-->

- **<Decision>.** <Why, and what lost.> — [<adr-id>](../decisions/<file>.md)

## Slice 1 — <name>

**Acceptance:** <the observable condition that closes this slice, in one sentence.>

<!-- Optional: what blocks this slice, or what it blocks. Keep it to a line. -->

- [ ] <task — one commit>
- [ ] <task — the non-obvious ones carry their reasoning inline, since that is what a reader needs>

## Slice 2 — <name>

**Acceptance:** <…>

- [ ] <task>

## Open questions

<!--
Unanswered questions are expected — they are answered when the task is reached, not before
starting. Attach one to the slice that trips over it; collect here only those belonging to no
single slice.
-->

## Out of scope

<!-- What was deliberately cut, so a reader can tell a decision from an oversight. -->

## Risks

<!-- What could derail the phase, and the mitigation. Only real ones. -->

---

## Closing the phase

When the phase ends, this document is compacted rather than deleted or left as-is:

1. **Migrate what outlives it, first.** A decision to [decisions/](../decisions/), an operational procedure to [operations.md](../operations.md) or [setup/deployment.md](../setup/deployment.md), a library choice to [tech-stack.md](../tech-stack.md), a measured baseline to the document that will be compared against it, a concept to [thesis/](../thesis/). **No permanent document may cite a phase plan as its source of truth** ([AGENTS.md](../../AGENTS.md) → Documentation discipline).
2. **Keep the slices table.** It is the roll-up, and the PR column is the trail back to the diff.
3. **Compact each closed slice to a short section** — what it contained and where its permanent knowledge now lives. A paragraph or a few ticked boxes, not the working notes.
4. **Leave the open slices in full**, at the end, after a `---`. Detail is what makes them actionable; the closed ones no longer need it.
5. **Keep the open decisions and questions** at the very end. They are the only part still doing work.
6. **Add a row to [open-items.md](open-items.md) for every item left open**, pointing back at the section here. A later phase starts while these are unfinished, and that file is where they stay visible.
