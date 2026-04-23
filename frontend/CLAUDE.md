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

- **MUI is the only UI library.** No Tailwind, no Chakra, no Radix. If something is missing, build it with MUI primitives + `sx`. Decision and rejected alternatives in [../docs/frontend-decisions.md](../docs/frontend-decisions.md) §7.
- **Styling via `sx` prop** for component-local styles; theme tokens for anything shared (colors, spacing, breakpoints).
- **Responsive is mandatory.** Mobile-first. Test at 360px, 768px, 1280px. Never hardcode pixel widths on layout containers.
- Exactly **one viewport meta tag** in `index.html`: `<meta name="viewport" content="width=device-width, initial-scale=1" />`.
- Icons: `@mui/icons-material` only. Use **per-icon imports** (`import FooIcon from '@mui/icons-material/Foo'`) — the barrel import breaks tree-shaking and pulls megabytes of unused icons.
- **Toasts:** `notistack` (`SnackbarProvider` at root, inside `ThemeProvider`). `useSnackbar()` from components; React Router actions return `{ toast }` and a page-level hook dispatches; imperative `enqueueSnackbar` is reserved for cross-cutting places like the `openapi-fetch` middleware that surfaces 401s. See decisions §12.

### Routing

- React Router **v7** (not v6). Data-router APIs are first-class in this project: `createBrowserRouter`, a root `loader` that owns auth state, `action` for auth and form mutations, `redirect()` from loaders and actions, and `lazy: () => import(...)` for route-level code splitting (decisions §4). Element-only routes remain valid for screens without data or mutation needs.

### State and data

- **Server state:** typed `openapi-fetch` client in `src/api/client.ts`; schema generated via `pnpm gen:api` from the backend's `/openapi.json`. From Phase 2 onward, wrapped with TanStack Query for caching, dedup, and refetch. See decisions §10 and §11.
- **openapi-fetch body-stream gotcha.** `apiClient.POST(...)` returns `{ data, error, response }`. The library has already consumed the response body to populate `data` / `error`, so calling `response.json()` / `response.text()` downstream throws (body is a one-shot stream). Destructure `{ data, error, response }` at the call site and use them — don't pass only `response` around and try to re-parse.
- **Auth state:** React Router v7 root `loader` + `useRouteLoaderData('root')`. No client-side store, no Zustand, no bespoke context, no `localStorage`. Login / register / logout flow through React Router `action`s that return `redirect(...)`; revalidation is automatic. See decisions §9.
- **Form state:** React Router `<Form method="post">` + `action` + `useActionData` for simple forms (<5 fields, no cross-field rules). `react-hook-form` + Zod from Phase 4 onward for simulation, recommendation, private-point and booking forms. See decisions §8.
- **Other client state:** `useState` + derived-during-render. Never store derived values in state.

### Env

- Only `VITE_*` variables are exposed to the browser — and **everything prefixed `VITE_` is public** (bundled into the build). Never put secrets in `frontend/.env`.
- **API base URL is not an env var.** Dev uses Vite's `server.proxy` to forward `/api/*` to the backend container; prod uses Nginx. The frontend always calls same-origin `/api/*` so the session cookie stays first-party.
- Map tile key (from Phase 2): `VITE_MAPTILER_KEY`. Public by design; lock it to the app's origins in the MapTiler dashboard. See decisions §2.

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
