---
id: fe-0006
status: accepted
phase: 3
date: 2026-06
related: [fe-0001]
---

# fe-0006: Use Biome for frontend linting and formatting

**Decision.** The frontend uses [Biome](https://biomejs.dev) (v2, pinned) as the single tool for linting, formatting, and import sorting, replacing ESLint + Prettier. Configuration lives in [frontend/biome.json](../../frontend/biome.json); `pnpm run lint` runs `biome check` (lint + format check + import sort) and `pnpm run format` runs `biome check --write`.

**Rationale.** Same framing as [fe-0001](fe-0001-mui.md): this is a solo thesis whose contribution is the application as a whole, and the frontend toolchain should be low-maintenance, not a project in itself. Biome is a single fast Rust binary that does lint + format + import-organize from one config — the same consolidation the backend already gets from Ruff and uv, so the mental model is consistent across both halves of the repo. The trigger was concrete: Prettier had never actually worked here (config files were present but the package was never installed, and the pre-commit `format:check` hook called a script that did not exist), so a decision was forced rather than merely available.

The migration was low-risk because the existing ESLint setup avoided Biome's known weak spots: it used no type-aware rules (where Biome, lacking a TypeScript-compiler backend, is weakest), and its two React plugins map onto Biome rules — `useExhaustiveDependencies` / `useHookAtTopLevel` (react-hooks) and `useComponentExportOnlyModules` (react-refresh). The load-bearing per-path `@mui/icons-material` import ban from fe-0001 ports directly to Biome's `noRestrictedImports`, error message intact. Biome's `recommended` set is also stricter than the prior config (a11y rules, `noArrayIndexKey`), which surfaced and fixed a handful of pre-existing issues on adoption.

**Implementation.** `@biomejs/biome` pinned at 2.5.0. `biome.json` enables the `recommended` preset plus the three React rules and the `noRestrictedImports` MUI guard; Prettier's settings were carried over via `biome migrate prettier` (single quotes, no semicolons, trailing commas, line width 100). Removed: `eslint`, `@eslint/js`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals`, `typescript-eslint`, plus `eslint.config.js`, `.prettierrc.json`, `.prettierignore`. `package.json` scripts: `lint` → `biome check`, `format` → `biome check --write`. The two frontend pre-commit hooks (eslint + the broken prettier check) collapse to one `frontend-biome` hook; CI's `pnpm run lint` now runs Biome. `public/` is excluded from analysis (static assets); the idiomatic Vite `getElementById('root')!` in `main.tsx` is left as a non-blocking `noNonNullAssertion` warning.

**Rejected alternatives.**

- *Finish the ESLint + Prettier setup.* The conventional, most popular React choice and the lowest-churn path. Rejected: it keeps two tools plus the `eslint-config-prettier` conflict layer, Prettier was non-functional anyway, and it forgoes the speed and consolidation that motivated the switch and that the backend already enjoys (Ruff lints the backend in ~70 ms; Biome brings the same profile to the frontend).
- *Keep ESLint for linting, use Biome only as the formatter.* A defensible hybrid that retains ESLint's best-in-class react-hooks linting. Rejected: still two tools, and full Biome's only real losses — a marginally less battle-tested hooks linter and no exact react-refresh equivalent (a dev-only HMR warning) — are acceptable for a thesis app whose frontend is a demo surface.
- *oxlint / other Rust linters.* Fast, but linter-only with an immature formatter; Biome covers both lint and format in one tool.

**References.**

- [Biome documentation](https://biomejs.dev) — getting started and the migrate-from-ESLint-&-Prettier guide.
- [fe-0001](fe-0001-mui.md) — the per-icon-import rule Biome now enforces.
