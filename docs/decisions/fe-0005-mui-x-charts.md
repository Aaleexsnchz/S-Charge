---
id: fe-0005
status: accepted
phase: Phase 5 (owner dashboard); first installed during Phase 3
date: 2026-06
related: [fe-0001]
---

# fe-0005: MUI X Charts for in-app charts

> Append revisions below with date and reason rather than editing in place.

**Revisions.**

- *2026-06-12* — originally adopted for a user-facing ACN analytics dashboard (Phase 3 slice 3). That dashboard was removed the same day when ACN was demoted to internal modelling data; the library stays for the owner dashboard charts (Phase 5) and the simulation result view (Phase 4). ACN analysis moved to a Jupyter notebook outside the app.

**Decision.** In-app charts (owner per-point stats, predicted-session visualisation) render with [MUI X Charts](https://mui.com/x/react-charts/) (community edition, MIT). Small bespoke visuals (e.g. hour-grid heatmaps) are hand-rolled MUI components rather than Pro-tier chart features.

**Rationale.** The app is already MUI v7 end to end ([fe-0001](fe-0001-mui.md)); X Charts ships from the same team, inherits the theme with zero glue code, and keeps a single UI vendor. The community edition covers the needed chart types (bar/line series) at no cost; the only gated component relevant to us (heatmap, Pro tier) is ~40 lines of `Box` grid by hand.

**Rejected alternatives.**

- *Recharts.* The ecosystem default and perfectly capable, but it doesn't know about the MUI theme (manual colour plumbing per chart); buys nothing over X Charts here.
- *Nivo.* Free native heatmap and good looks, but a parallel theming system and per-package bundles for one component that is trivial to hand-roll.
- *Hand-rolled SVG/canvas.* Axis/scales/tooltips/responsive sizing are exactly the undifferentiated work a library should do.

**References.**

- MUI X Charts documentation (community vs Pro feature matrix)
- [phases/phase-5.md](../phases/) — owner dashboard slice (written when the phase starts)
