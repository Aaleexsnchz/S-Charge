---
id: fe-0001
status: accepted
phase: Phase 1 / Slice 4
date: 2026-06
---

# fe-0001: Use MUI (Material UI) as the frontend component library

> Foundational frontend decision. Append revisions below with date and reason rather than editing in place.

**Revisions.**

- *2026-06 — Biome replaces ESLint + Prettier ([fe-0006](fe-0006-biome.md)).* The per-path `@mui/icons-material` import rule described under *Implementation* below is now enforced by Biome's `noRestrictedImports`, not the ESLint rule referenced there.
- *2026-06-21 — scope pivot ([PLAN.md](../PLAN.md) revision 2026-06-21).* The *Rationale* below frames the academic contribution as "Phases 3–4 (ACN import, distribution fitting, …)". That framing is superseded: ACN is dropped and the thesis core is now the application itself, with the charging optimiser and AI as value-add features. The MUI decision is unaffected.

**Decision.** The PWA is built with [MUI](https://mui.com) (Material UI) as the component library, styled via [Emotion](https://emotion.sh) (`@emotion/react` + `@emotion/styled`). Theming, typography (Inter + JetBrains Mono via `@fontsource`), and a shared palette are centralised in a single MUI theme. Icons are imported per-path from `@mui/icons-material` (never from the barrel).

**Rationale.** This is a solo thesis project on a fixed timeline, and the academic contribution sits in Phases 3–4 (ACN import, distribution fitting, smart-charging algorithm). The frontend exists to demo that work, not to be a CSS exercise. MUI ships the surface the app actually needs out of the box: form controls with validation styling, data grid, dialogs and bottom sheets, navigation primitives, snackbars (via [notistack](https://notistack.com/)), accessible focus rings, ARIA defaults and keyboard handling. Spanish copy is component-prop driven — no i18n library required at this stage. Emotion's runtime CSS-in-JS carries a measurable bundle and parse cost vs. zero-runtime alternatives, accepted as the price of MUI's documented happy path.

The per-icon import rule is load-bearing: a single `import { Foo } from '@mui/icons-material'` pulls the entire icon manifest into the chunk and silently kills tree-shaking.

**Implementation.** Phase 1 / Slice 4. `frontend/` is a Vite + React 19 + TypeScript scaffold. MUI + Emotion configured in `frontend/src/main.tsx` with a `ThemeProvider`; fonts loaded via `@fontsource/inter` and `@fontsource/jetbrains-mono`; `notistack` mounted at the root for snackbars. ESLint rule enforces per-path icon imports. Mobile-first at 360px reference width.

**Rejected alternatives.**

- *shadcn/ui + Tailwind.* Strongly considered late in scoping — modern, more current in the React ecosystem in 2026, and the developer had prior experience with the stack. Rejected because (a) every component is built/composed by the user rather than installed, which is more frontend churn for a backend-heavy thesis; (b) no batteries-included data grid, form layer, or dialog system at the maturity MUI ships; (c) the thesis timeline does not absorb a second learning curve on the UI layer. An earlier draft of the plan specified shadcn before this trade-off was reconsidered.
- *Chakra UI.* Comparable component surface but a smaller ecosystem and a documented v3 migration churn; no incremental benefit over MUI for this project's needs.
- *Mantine.* Strong feature set, less mainstream in 2026, smaller community, more risk of dead-end Stack Overflow searches at 02:00 the week before defence.
- *Vanilla CSS + hand-rolled components.* Maximum control, disproportionate cost for a thesis whose contribution is elsewhere.

**References.**

- MUI v7 documentation
- Emotion documentation
- [thesis/frontend.md](../thesis/frontend.md) — concept-level summary (written when the chapter is needed).
