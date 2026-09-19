# AI assistant

**Status:** ⬜ Planned, **cut** · **Phase** [13](../plan/plan.md)

A natural-language layer over the app's own APIs — points, simulate, recommend, bookings, prices — as tools. No new data sources. Prices, costs, schedules and ledger movements stay deterministic and are computed by the existing services; the model orchestrates and explains.

## Planned

**The feature set is not decided.** The candidates live in [ideas-backlog.md](../ideas-backlog.md) — a tool-calling trip assistant, explain-the-schedule, conversational point search, habit-based suggestions — and the choice is made at the start of the phase against the time actually remaining, then recorded in the phase plan.

Decisions that come with it: how deep to go, which model (default to the latest capable Claude model, recorded by exact id), where the deterministic/LLM boundary sits, API spend and key handling in the prod stack, and what the UI does when the model is unavailable — the demo must survive it.
