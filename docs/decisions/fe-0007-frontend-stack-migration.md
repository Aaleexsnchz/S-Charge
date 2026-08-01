---
id: fe-0007
status: proposed
supersedes: [fe-0001]
phase: 6
date: 2026-08
related: [fe-0002, fe-0003, fe-0004]
---

# fe-0007: Migrate the frontend from MUI to Tailwind + shadcn/ui, and adopt TanStack Router + Form

**Decision.** The frontend moves off **MUI + Emotion** onto **Tailwind CSS v4 + shadcn/ui**, off **React Router** onto **TanStack Router**, and gains a form layer it never had: **TanStack Form + Zod**. Charts move from MUI X Charts to shadcn's chart layer, and notistack to sonner. The *s-charge* design system is preserved — its tokens are re-expressed as Tailwind theme tokens, not redesigned. Supersedes [fe-0001](fe-0001-mui.md); [fe-0002](fe-0002-pwa.md) (PWA), [fe-0003](fe-0003-maplibre-openfreemap.md) (map) and [fe-0004](fe-0004-tanstack-query.md) (TanStack Query) are unaffected.

**Rationale.** Four reasons, in the order they carry weight:

1. *Emotion serialises styles at runtime, on every render.* Tailwind resolves styling at build time: no styling engine in the bundle, nothing to serialise. `/map` scored **31** on Lighthouse Performance under mobile throttling in Phase 2; the map engine dominates that, but the CSS-in-JS cost is additive and avoidable.
2. *shadcn/ui copies component source into the repository.* Adapting the design system becomes editing our own files rather than overriding a vendor's from outside — the 116 `sx` call sites are the symptom of the current arrangement.
3. *TanStack Router types route params and search params at compile time*, converting a class of runtime bug into a build error, and makes URL-held UI state (the map filters) practical without hand-written validation.
4. *There is no form abstraction today.* The point-registration wizard is the first real form; one Zod schema can validate client-side and mirror what Pydantic enforces server-side.

**The timing is the decisive argument, not the reasons above.** Migration cost grows with every phase: ~10 screens now, ~18 after private points, the optimiser, bookings and the wallet. Building those screens on a stack we intend to abandon is the actual waste. This is a now-or-never decision and the answer is now.

**Consequences.**

- Work MUI provided for free returns to us: bottom navigation becomes ~30 lines we own, snackbars move to sonner, and accessibility now rests on headless primitives plus our own markup rather than a mature component library's defaults.
- The `@mui/icons-material` barrel ban in [fe-0001](fe-0001-mui.md) transfers to `lucide-react`; Biome's `noRestrictedImports` rule moves with it.
- Every screen must be re-checked on a real phone at 360px. This is the one part no tool verifies, and the reason the migration is a phase of its own rather than incremental work alongside features.
- Lighthouse and bundle size are measured before the first change and after, and the result is published whatever it shows.
- The project carries two styling systems for the duration of the phase and must not exit it in that state.

**Rejected alternatives.**

- *Stay on MUI.* Zero cost, working UI. Rejected on timing: not migrating now is equivalent to never migrating, and every later phase is then built on a base we would not choose again.
- *Stay on MUI, move to a zero-runtime engine (Pigment CSS).* Would address reason 1 while keeping the component API. Rejected because MUI's own documentation describes Pigment CSS as **early alpha**, and it addresses none of reasons 2–4. Betting a fixed-deadline thesis UI on an alpha styling engine is a poor trade.
- *Styles only; keep React Router.* The routing files are rewritten anyway when the screens are, so the saving is smaller than it looks and the typed-routing benefit is forfeited.
- *Incremental, screen by screen, alongside feature work.* Superficially the prudent option and in fact the worst: two styling systems coexisting in a ~3,200-line codebase for weeks, two ways to do everything, double the review surface.

**References.**

- [thesis/migracion-del-stack.md](../thesis/migracion-del-stack.md) — the full argument, in Spanish, including the other stack changes (PostgreSQL 18, Python 3.13, native dev, tooling) and the evaluation method. This ADR is the repo-facing record; that chapter is the thesis-facing one.
- [tech-stack.md](../tech-stack.md) — per-library status: shipped / Phase 6 / leaving.
