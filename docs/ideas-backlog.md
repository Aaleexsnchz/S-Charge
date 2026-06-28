# Ideas backlog

Deferred ideas parked for the "decide later" moment — nothing here is committed scope.
Pull from this list when a phase has slack or when deciding the AI layer's depth. When an
idea is promoted, move it into [PLAN.md](PLAN.md) (a phase + acceptance criteria) and
remove it here.

## AI / agent features (Phase 8 — pick from here)

AI is now a committed **Phase 8** (planned), but the **specific features are not yet decided** —
this is the menu to choose from. All call the app's own APIs (points, simulate, recommend,
bookings, prices) as tools — no new data sources. Depth scales to remaining hours.

- **NL charging/trip assistant** — a tool-calling agent that plans a charge or trip
  end-to-end: find a point → simulate the session for the user's car → optimise the
  schedule → create the booking. The flagship idea; the most thesis-worthy as a chapter.
- **Explain-the-schedule** — natural-language rationale for the optimiser's output
  ("why these hours, how much you save vs charging now").
- **Conversational point search** — "cheapest CCS near me under 0.40 EUR/kWh available
  now" → structured query over the catalogue + filters.
- **Habit-based booking suggestions** — infer routine from session history and propose
  the next booking / best time to charge.
- **Owner-dashboard insight summaries** — revenue/utilisation trends in plain language.
- **"Best time to charge tonight"** — proactive nudge derived from the PVPC curve and the
  user's car + departure time.
- **Compatibility Q&A** — answer vehicle/connector/charging questions from the vehicle
  catalogue and point metadata.

Open decisions when promoting: which model (default to the latest capable Claude model);
tool-calling vs. plain prompt; where the boundary sits between deterministic services and
the LLM (keep money/optimisation deterministic, let the LLM orchestrate and explain).

## Product / platform (non-AI deferred)

- **Real payments** — replace the simulated wallet/ledger with a real processor
  (e.g. Stripe test mode) + commission tracking on the owner dashboard. Carries PCI /
  compliance weight — intentionally out of the thesis timeline.
- **Route optimisation (minimal)** — origin/destination → route polyline from a free
  routing API (OSRM / OpenRouteService) → corridor-query points along it → rank by
  detour + price + predicted session. No consumption modelling, no custom routing engine.
- **Commission / marketplace economics** — platform fee on public-point sessions, payout
  flows, owner statements.

## Notes

- The original ACN-Data integration (real-session-grounded occupancy + simulation
  realism) was **dropped, not deferred** — it is not a backlog item. It lives only as a
  documented road-not-taken in [thesis/indice.md](thesis/indice.md).
