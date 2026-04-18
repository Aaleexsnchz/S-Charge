# Frontend — React + Vite PWA

See root [CLAUDE.md](../CLAUDE.md) for project orientation and [PLAN.md](../PLAN.md) for roadmap.

## Stack

React 19, Vite 8, TypeScript 5.9, MUI 7 (Emotion), React Router 7, Vitest + Testing Library, ESLint + typescript-eslint. Package manager: **pnpm**.

## Layout

```text
src/
├── assets/       static imports (images, fonts)
├── layouts/      page shells (AppShell, AuthLayout)
├── pages/        route-level components (one per route)
├── styles/       global CSS overrides, theme tokens
├── theme.ts      MUI theme
├── router.tsx    React Router config
├── main.tsx      entry point
└── index.css     global baseline
```

Add as needed: `components/`, `hooks/`, `api/`, `types/`, `utils/`. Prefer feature-folders over type-folders once the app grows (`features/charging-points/` containing its own components, hooks, API calls).

## Conventions

### Language-level

- File naming: **PascalCase** for components (`MapView.tsx`), **camelCase** for utils and hooks (`useStations.ts`, `formatPrice.ts`).
- One component per file. Co-locate tests as `Foo.test.tsx` next to `Foo.tsx`.
- Functional components only. No class components.

### React 19 specifics

- **`ref` is a regular prop** — no `forwardRef` wrapper.
- **`use()`** replaces most `useContext()`; can also unwrap promises in Suspense.
- Derive values during render instead of storing in state + effects.

### UI

- **MUI is the only UI library.** No Tailwind, no Chakra, no Radix. If something is missing, build it with MUI primitives + `sx`.
- **Styling via `sx` prop** for component-local styles; theme tokens for anything shared (colors, spacing, breakpoints).
- **Responsive is mandatory.** Mobile-first. Test at 360px, 768px, 1280px. Never hardcode pixel widths on layout containers.
- Exactly **one viewport meta tag** in `index.html`: `<meta name="viewport" content="width=device-width, initial-scale=1" />`.
- Icons: `@mui/icons-material` only.

### Routing

- React Router **v7** (not v6). Use the modern data-router APIs (`createBrowserRouter`, `loader`, `action`) where they help; fall back to element routes when they don't.

### State and data

- Server state: fetch via `fetch` + a small typed API layer in `src/api/`. Introduce TanStack Query only if caching/dedup becomes painful.
- Client state: `useState` + context. Don't reach for Zustand/Redux until it's clearly needed.
- Never store derived values in state.

### Env

- Only `VITE_*` variables are exposed to the browser — and **everything prefixed `VITE_` is public** (bundled into the build). Never put secrets in `frontend/.env`.
- Config consumed via `import.meta.env.VITE_API_URL`.

### Testing

- Vitest + Testing Library. Test behavior, not implementation.
- Run: `pnpm test`. Watch: `pnpm vitest`.

### Lint / format

- `pnpm lint` must pass before commit. Typecheck runs as part of `pnpm build`.

## Commands

```bash
pnpm install              # install deps
pnpm dev                  # dev server (Vite)
pnpm build                # typecheck + production build
pnpm lint                 # ESLint
pnpm test                 # Vitest (run mode)
```

When running in Docker (the default), see root [DOCKER.md](../DOCKER.md) — code changes hot-reload automatically; `package.json` changes need a rebuild.
