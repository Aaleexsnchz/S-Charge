---
id: fe-0001
status: superseded
superseded_by: fe-0007
phase: 1
date: 2026-06
---

# fe-0001: Use MUI (Material UI) as the frontend component library

> **Superseded by [fe-0007](fe-0007-frontend-stack-migration.md).** Kept because it explains why the codebase looks the way it does today, and because the reversal is itself thesis material. The record below is the decision as taken; it is not current.

**Decision.** The PWA is built with [MUI](https://mui.com) (Material UI) as the component library, styled via [Emotion](https://emotion.sh) (`@emotion/react` + `@emotion/styled`). Theming, typography (Inter + JetBrains Mono via `@fontsource`), and a shared palette are centralised in a single MUI theme. Icons are imported per-path from `@mui/icons-material` (never from the barrel), enforced by Biome's `noRestrictedImports` ([fe-0006](fe-0006-biome.md)).

**Rationale.** This is a solo thesis project on a fixed timeline, and the contribution is the application as a whole, not its styling layer. The frontend exists to demo the product, not to be a CSS exercise. MUI ships the surface the app actually needs out of the box: form controls with validation styling, data grid, dialogs and bottom sheets, navigation primitives, snackbars (via [notistack](https://notistack.com/)), accessible focus rings, ARIA defaults and keyboard handling. Spanish copy is component-prop driven — no i18n library required at this stage. Emotion's runtime CSS-in-JS carries a measurable bundle and parse cost vs. zero-runtime alternatives, accepted as the price of MUI's documented happy path.

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
- [thesis/migracion-del-stack.md](../thesis/migracion-del-stack.md) — why this decision was right when taken, and why it expired.
