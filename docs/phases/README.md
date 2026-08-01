# Phase plans

One document per phase: the detailed plan for that phase and nothing else. [plan.md](../plan.md) says *what* each phase is and when it is done; these say *how* it gets built.

A phase plan is **written just before the phase starts**, never in advance. Writing it early produces a plan whose decisions were taken without the information needed to take them — the useful work is raising the questions, arguing them out, and recording what was settled and what was rejected, and that can only happen against the code as it actually is.

The plan stays **live** for the phase's duration: slice statuses move, open questions get answered in place, and scope that turns out to be wrong is rewritten. It states current reality only — no dated revision blocks. These are working plans, not documentation: what must outlive the phase gets migrated out when it closes ([AGENTS.md](../../AGENTS.md) → Documentation discipline).

| Phase | Plan |
| --- | --- |
| 1 — Foundation | [phase-1.md](phase-1.md) |
| 2 — REVE seed + Map | [phase-2.md](phase-2.md) |
| 3 — Simulation + algorithm | [phase-3.md](phase-3.md) |
| 4 — Frontend redesign + dashboard-first IA | [phase-4.md](phase-4.md) |
| 5 — Deployment + CI/CD + releases | [phase-5.md](phase-5.md) |

Phases 6–13 are described in [plan.md](../plan.md); their plans get written when they start.

## Structure

Phases 1–4 are closed and kept short — a slice table, what each slice contained, and anything still pending. A plan for a phase about to start carries more:

- **Intro** — what this phase builds, the document that owns the model or rationale behind it, and what the phase's goal is in one paragraph.
- **Slices table** — one branch and one PR each, in order, with what blocks what. Sized so no PR becomes unreviewable.
- **Decisions taken** — the calls settled while planning, each with the alternatives that were rejected and why. This is the part that ends up in the thesis.
- **Tasks** — one commit each, under their slice, with an acceptance line per slice. Give tasks an id and a rough size when the phase is big enough that ordering matters.
- **Open questions** — attached to the task that trips over them, and collected at the end when they belong to no single task. **Unanswered questions are expected**: they are answered when the task is reached, not before starting.
- **Out of scope** — what was deliberately cut, so a reader can tell a decision from an oversight.
- **Risks** — what could derail the phase, and the mitigation.

Not every phase needs every section. A phase with no real risks should not invent any.
