# Frontend Architecture — Decision Record

Background notes for the frontend stack beyond what [PLAN.md](../PLAN.md) records in the Tech Stack table. Each entry captures a decision, its rationale, how it is realised, the alternatives considered and rejected, and primary references suitable for citation in the thesis.

The map and chart choices interact with Phase 2 (REVE map), Phase 3 (ACN analytics), and Phase 6 (deployment + performance polish). Code-splitting and Lighthouse strategy cut across all phases. These decisions are locked once committed; subsequent changes should be appended as new entries (with date and reason) rather than edited in place.

---

## 1. Map library: MapLibre GL JS via `react-map-gl`

**Decision.** The `/map` route renders through [MapLibre GL JS](https://maplibre.org/) v4+, wrapped in the `react-map-gl/maplibre` component bindings. Leaflet and Mapbox GL are not used.

**Rationale.**

- *Vector tiles over raster.* The map is a hero surface of the PWA (REVE network in Phase 2, user-contributed private points in Phase 5). Vector tiles provide smooth zoom, retina-sharp rendering on mobile, and style-at-render-time — all visually superior to Leaflet's raster baseline. The quality delta is obvious on a phone and matters for thesis demo day.
- *Open-source and vendor-neutral.* MapLibre is the community fork of Mapbox GL JS v1 (the last fully-open-source Mapbox release before the v2 licence change). API surface is identical to Mapbox GL; swapping tile providers is a style-JSON change, not a code change. This preserves the "no Supabase / no Vercel / no vendor lock-in" posture documented in the root CLAUDE.md.
- *React integration is first-class.* `react-map-gl` (originally a Mapbox wrapper) now has a `maplibre` submodule with declarative `<Map>`, `<Source>`, `<Layer>`, `<Marker>`, `<Popup>` components. Mirrors the ergonomics of `react-leaflet` with a meaningfully better runtime.
- *Marker clustering is built in.* GeoJSON sources accept `cluster: true` + `clusterRadius`, and unclustered/clustered layers are styled via standard paint expressions. No third-party clustering plugin (contrast with Leaflet, which needs `react-leaflet-cluster`).
- *Thesis defensibility.* Using the dominant open-source WebGL map stack is straightforwardly defensible ("industry-standard vector tiles via the maintained open-source fork of Mapbox GL").

**Implementation.** Phase 2. `pnpm add maplibre-gl react-map-gl pmtiles`. MapLibre protocol handler for PMTiles is registered once at app bootstrap (see §2). Map component is code-split as the `/map` route chunk (see §4) so its ~200 KB gzip cost is only paid on first navigation to `/map`.

**Rejected alternatives.**

- *Leaflet + OSM raster.* Smallest bundle (~50 KB) and lowest learning curve, but the raster aesthetic looks dated on high-DPI phones and cannot express Phase 5 overlays as cleanly. The ~150 KB bundle delta is absorbed by route-level code splitting (§4).
- *Mapbox GL JS v2/v3.* Proprietary licence since 2020. Free tier of 50 000 map loads/month is sufficient for a thesis demo but introduces vendor risk if the app outlives the thesis, and the public token model complicates the "zero commercial dependency" story. MapTiler's free tier (§2) is more generous for the same API.
- *Google Maps JavaScript API.* Non-trivial cost past the free tier, prohibits data caching in several clauses, and the licensing is unsuited to a deployed thesis demo with unknown traffic.
- *OpenLayers.* Capable and open-source, but the React ecosystem is thinner and the API is more imperative than `react-map-gl`. Not worth the ergonomic regression given MapLibre covers the same feature set.

**References.**

- MapLibre GL JS documentation — <https://maplibre.org/maplibre-gl-js/docs/>
- `react-map-gl` MapLibre guide — <https://visgl.github.io/react-map-gl/docs/get-started/get-started>
- Mapbox licence change announcement (December 2020) — the event that produced the MapLibre fork
- OpenStreetMap Foundation, *Tile Usage Policy* — constraints that push serious deployments off osm.org tiles

---

## 2. Vector tiles: MapTiler as primary, self-hosted Protomaps documented as fallback

**Decision.** The production tile source is [MapTiler](https://www.maptiler.com/) via its free tier (100 000 tile requests/month). The MapLibre style URL is composed at runtime from a public Referer-locked API key (`VITE_MAPTILER_KEY`). A self-hosted [Protomaps](https://protomaps.com/) `.pmtiles` extract of Spain served through Nginx is documented as the Phase 6 (or post-thesis) fallback if MapTiler becomes unsuitable, but is explicitly not on the Phase 2 critical path.

**Rationale.**

- *Ops cost for self-hosting eats Phase 2 budget.* Self-hosting ~200 MB of PMTiles plus font glyph PBFs and a sprite sheet, rewriting a style JSON, configuring Nginx range requests and cache-control, and wiring the `pmtiles://` protocol handler is an afternoon of work. That afternoon comes out of Phase 2's 25–30h budget — the phase with the highest density of unknowns (filter UI, mobile polish, Google Maps redirect). The thesis contribution lives in Phases 3–4, not the tile pipeline.
- *The free tier is ~15× the demo's needs.* 100 000 requests/month comfortably covers a thesis demo with traffic in the low thousands of requests per month. The "quota to watch" concern from the previous framing does not materialise at this scale.
- *Vendor coupling is one public env var.* `VITE_MAPTILER_KEY` is bundled into the client (every `VITE_*` variable is public), so there is no secret to rotate. MapTiler authenticates keys by HTTP Referer — locking the key to `http://localhost:5173` and the production domain in the MapTiler dashboard prevents cross-origin abuse. This is the standard model for client-side map keys; it is not a secret in the cryptographic sense.
- *The thesis "open stack" narrative does not require self-hosting.* "MapLibre GL JS rendering OpenStreetMap-derived vector tiles" is already a fully open stack from the browser down to the data licence. Whether the tiles are served from a vendor CDN or our Nginx is a deployment choice, not an architectural one. The open-stack claim in Chapter 4 is unaffected.
- *The fallback path is asymmetric in the right direction.* MapTiler-first + self-host-later leaves a working demo in between the two configurations. Self-host-first + MapTiler-fallback-if-needed means shipping no map until self-hosting is done. Given Phase 2 schedule risk, the MapTiler-first ordering dominates.

**Implementation.** Phase 2. `pnpm add maplibre-gl react-map-gl`. `VITE_MAPTILER_KEY` added to [frontend/.env](../frontend/.env) and [frontend/.env.example](../frontend/.env.example). The MapLibre style URL is composed at render time:

```ts
const styleUrl = `https://api.maptiler.com/maps/streets-v2/style.json?key=${import.meta.env.VITE_MAPTILER_KEY}`
```

No PMTiles protocol registration, no `/tiles/` static directory, no dedicated Nginx location block. The key is Referer-locked in the MapTiler dashboard to the dev and production origins.

**Phase 6 fallback (documented, not on the critical path).** If (a) the app outlives the thesis and sees organic traffic, or (b) an examiner asks about deployment sovereignty, the self-hosted Protomaps path is:

- Pull `spain.pmtiles` from [protomaps.com/builds](https://protomaps.com/builds/) (~200 MB), font glyph PBFs and sprite sheet from [protomaps/basemaps-assets](https://github.com/protomaps/basemaps-assets).
- Place them in `frontend/public/tiles/` (dev) or serve them from a dedicated Nginx `location /tiles/` in prod.
- Register the PMTiles protocol handler once in `main.tsx`:

  ```ts
  import maplibregl from 'maplibre-gl';
  import { Protocol } from 'pmtiles';
  maplibregl.addProtocol('pmtiles', new Protocol().tile);
  ```

- Swap the style JSON's `sources[].url` from the MapTiler URL to `pmtiles:///tiles/spain.pmtiles`.
- Nginx serves `/tiles/*` with HTTP range requests (default behaviour), `Cache-Control: public, max-age=31536000, immutable`, gzip off on the `.pmtiles` file (already compressed; gzip would break range requests).

Nothing else changes — MapLibre abstracts the tile source, `react-map-gl` knows nothing about the provider. This path is validated architecturally; executing it is a Phase 6 decision keyed to actual operational signal.

**Rejected alternatives.**

- *Self-hosted Protomaps as primary (previous decision).* Flipped for the reasons above: ops cost out of proportion to a thesis demo's scale, steals time from Phase 2 feature work, fallback direction asymmetry.
- *Mapbox GL JS v2/v3.* Proprietary licence since 2020. Smaller free tier than MapTiler, and ties the deployment to the company whose licence change produced the MapLibre fork in the first place — poor thesis narrative.
- *Google Maps JavaScript API.* Non-trivial cost past the free tier, restrictive caching clauses, unsuited to a deployed thesis demo with unknown traffic.
- *OSM.org raster tiles via Leaflet.* Against the OSM Foundation's tile usage policy for deployed apps; also ruled out by the MapLibre-vector-tile decision in §1.

**References.**

- MapTiler Cloud pricing and free tier — <https://www.maptiler.com/cloud/plans/>
- MapLibre GL JS style specification — <https://maplibre.org/maplibre-style-spec/>
- Protomaps documentation (fallback path) — <https://docs.protomaps.com/>
- PMTiles specification (fallback path) — <https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md>
- Protomaps basemaps assets (fallback path) — <https://github.com/protomaps/basemaps-assets>

---

## 3. Charts: Apache ECharts via `echarts-for-react`

**Decision.** All analytics and simulation charts (Phase 3 `/statistics`, Phase 4 `/simulate`, Phase 5 owner dashboard) render through [Apache ECharts](https://echarts.apache.org/) v5+ via the `echarts-for-react` binding, with tree-shaken imports to keep the route chunk under ~200 KB gzip. Recharts, initially listed in PLAN.md, is not used.

**Rationale.**

- *Heatmap is a Phase 3 requirement.* The ACN utilization heatmap (hour × day-of-week, plus a calendar heatmap over the ACN sampling window) is central to the analytics narrative. ECharts supports both as first-class chart types with native `visualMap` tooltips and `dataZoom` brushing. Recharts has no native heatmap — implementing one requires a grid of `<Cell>` elements with manual colour scales, which looks amateur and does not scale interactively.
- *Dataset scale.* ACN-Data is tens of thousands of sessions. Recharts renders to SVG, which degrades noticeably above ~1 000 DOM nodes. ECharts renders to Canvas by default (WebGL available for >100 k points) and handles the ACN scale without special effort.
- *Chart breadth.* Phase 3–4 need at least: line + area (energy over time, predicted session with confidence band), grouped bar (per-station comparison), histogram (session-duration distribution), heatmap (utilization), calendar heatmap (daily usage), and box plots (dwell-time spread). ECharts covers all of these natively; Recharts covers half and requires Visx-style primitives for the rest.
- *Thesis contribution lives in Phase 3–4.* Per the project-level "break-even" rule (memory: library-backed for non-core phases, from-primitives reserved for where the academic contribution lives), the chart *library* should not be the ceiling on analytics quality. ECharts raises that ceiling; Recharts would lower it.
- *Bundle cost is acceptable.* Tree-shaken ECharts with only the chart types and components we actually use compiles to ~150 KB gzip, loaded only on `/statistics` and `/simulate` via the route-split strategy in §4. Comparable to Recharts (~100 KB) once both are scoped to their routes.

**Implementation.** Phase 3. `pnpm add echarts echarts-for-react`. Tree-shaken imports registered once in a `src/charts/echarts.ts` barrel module:

```ts
import * as echarts from 'echarts/core';
import {
  LineChart, BarChart, HeatmapChart, ScatterChart, CustomChart,
} from 'echarts/charts';
import {
  GridComponent, TooltipComponent, LegendComponent,
  VisualMapComponent, CalendarComponent, DataZoomComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  LineChart, BarChart, HeatmapChart, ScatterChart, CustomChart,
  GridComponent, TooltipComponent, LegendComponent,
  VisualMapComponent, CalendarComponent, DataZoomComponent,
  CanvasRenderer,
]);
```

Chart components receive a pre-built `option` object and pass it to `<ReactECharts option={...} />`. Configuration colocated with each page; shared style tokens (colour ramps, tooltip typography) live in `src/charts/theme.ts` and reference MUI theme tokens so light/dark parity is automatic.

**Rejected alternatives.**

- *Recharts.* React-idiomatic and fast to scaffold for line/bar, but the heatmap limitation alone is disqualifying. Choosing Recharts and then reaching for Visx to fill the heatmap gap would yield a mixed-library frontend — worse than committing to ECharts.
- *Visx (Airbnb).* Low-level D3 primitives as React components. Gives full control but means writing charts from primitives, which contradicts the break-even rule for non-core work (and the "academic contribution lives in Phase 3–4 analysis, not chart plumbing" framing). Retained mentally as a fallback if a specific simulation-output visual needs custom geometry.
- *Chart.js via `react-chartjs-2`.* Simpler than ECharts, Canvas-based, but no native heatmap and a smaller chart-type library. Same disqualification as Recharts.
- *D3 directly.* Maximum flexibility, maximum code volume. Wrong trade for Phase 3–4 scope.

**References.**

- Apache ECharts documentation — <https://echarts.apache.org/en/option.html>
- `echarts-for-react` — <https://github.com/hustcc/echarts-for-react>
- Recharts, *Heatmap example* (community) — demonstrates the Cell-grid workaround and why it's unsatisfactory
- ACN-Data, Lee et al. (2019) — the source dataset whose analytics shape the chart requirements

---

## 4. Route-based code splitting as the bundle strategy

**Decision.** Heavy route chunks (`/map`, `/statistics`, `/simulate`, `/my-points/new`) are loaded lazily via React Router v7's `lazy` route property. No manual `React.lazy` / `Suspense` wrappers at the component level. The app shell (shared layout, auth, navigation) remains a single eager bundle.

**Rationale.**

- *Largest single perf win.* MapLibre (~200 KB) and ECharts (~150 KB) are the two biggest libraries in the stack. Route-splitting defers both until the user actually navigates to the relevant page, and the service worker caches the chunk after first visit — so the app shell cost stays low and the "expensive" pages pay their cost exactly once per client.
- *React Router v7 supports this natively.* `createBrowserRouter([{ path: '/map', lazy: () => import('./pages/MapPage') }, ...])` is the documented pattern; no ecosystem plug-in, no build-tool config beyond Vite's default dynamic-import handling.
- *Composition with the PWA service worker.* Vite PWA plugin (Workbox under the hood) will precache route chunks once they are emitted with stable hashes. The combination is: "pay the chunk once on first visit, never pay it again while the app is installed."
- *No per-component `React.lazy`.* Component-level lazy boundaries fragment the waterfall and rarely pay off; route-level boundaries match how users actually navigate and keep the mental model simple.

**Implementation.** Phase 2 for the `/map` split, Phase 3 for `/statistics`, Phase 4 for `/simulate`. Router definition in `src/router.tsx` uses the `lazy` property for every page route that pulls a heavy dependency. Pages expose their component as a named `Component` export to match the React Router v7 lazy-route contract. No global loading spinner — each lazy route has a lightweight route-level fallback element.

**Rejected alternatives.**

- *Eager bundle with manual `React.lazy` on individual chart components.* Over-fragments the waterfall and still pays the MapLibre/ECharts cost on the shell if any non-lazy import accidentally references them.
- *Manual `vite.config.ts` `manualChunks`.* Works but fights Vite's automatic chunking heuristics; only necessary when automatic splitting produces a pathological graph, which it does not here.
- *Server-side rendering.* Vite SSR + React Router is viable but adds deployment complexity (Node runtime on the VPS alongside Uvicorn, hydration edge cases) that is disproportionate for a PWA whose first paint is an authenticated shell most of the time.

**References.**

- React Router v7 documentation, *Lazy loading* — <https://reactrouter.com/start/data/route-object#lazy-loading>
- Vite guide, *Code splitting* — <https://vite.dev/guide/features.html#build-optimizations>
- web.dev, *Code splitting with React.lazy and Suspense* — <https://web.dev/articles/code-splitting-suspense>

---

## 5. Lighthouse as milestone quality gate, not CI

**Decision.** Google Lighthouse audits (PWA, Performance, Accessibility, Best Practices) are run manually at four milestones: end of Phase 1 (PWA audit only), end of Phase 2 (full audit, baseline), end of Phase 3 (spot-check after charts land), and Phase 6 (full audit, recorded in the thesis evaluation chapter). Lighthouse is *not* wired into CI.

**Rationale.**

- *PWA installability is a hard requirement.* PLAN.md Phase 1 requires "Chrome shows Install app prompt and add from Safari" and Phase 6 requires "PWA installable from production on iOS + Android". Lighthouse's PWA audit is the canonical automated check for exactly this set of criteria (manifest, service worker, offline fallback, HTTPS, icons, viewport). Running it at milestones is the cheapest way to verify the hard requirement.
- *Accessibility is a cheap thesis win.* A Lighthouse Accessibility score ≥ 90 is reportable in the thesis evaluation chapter and signals WCAG AA competence. MUI's default components clear most of the checklist; what remains is colour contrast in custom theme tokens, aria-labelling on icon-only buttons, and focus-visible styles — all fixable in 1–2 hours per audit.
- *Mobile performance score replaces guesswork.* Lighthouse's throttled-4G Moto-G-class profile simulates exactly our target device class. The score is an empirical answer to "does this run well on a phone?" and complements real-device testing without replacing it.
- *CI integration is over-scope.* Lighthouse CI (`@lhci/cli`) works but requires a public URL, adds 2–5 minutes to every build, and produces flaky scores in containerised runners (CPU contention affects performance numbers). The gain — catching regressions the instant they land — is disproportionate for a solo-developer thesis. Milestone audits catch the same issues with a fraction of the infrastructure cost.

**Implementation.** No persistent infrastructure. Runs are initiated on demand via Chrome DevTools (preferred for the visual report) or `npx lighthouse https://<url> --view` from the CLI. Scores at the Phase 6 audit are transcribed into the thesis Chapter 6 (Evaluation). A short `docs/lighthouse-YYYY-MM-DD.md` note per audit records the four scores and any deferred issues.

**Rejected alternatives.**

- *Lighthouse CI on every PR.* See CI rationale above. Not worth the operational overhead for a solo-developer thesis.
- *Web Vitals in-app reporting.* `web-vitals` with a self-hosted RUM endpoint is standard for production SaaS and is out of scope here — the thesis demo does not have enough traffic to produce meaningful percentiles.
- *No Lighthouse at all, relying on real-device feel.* Real devices catch UX but miss the accessibility and PWA-manifest categories. Lighthouse is cheap enough at milestone cadence that skipping it is not worth the risk.

**References.**

- Google, *Lighthouse documentation* — <https://developer.chrome.com/docs/lighthouse/overview>
- web.dev, *Progressive Web App checklist* — <https://web.dev/articles/pwa-checklist>
- WCAG 2.1 — <https://www.w3.org/TR/WCAG21/>

---

## 6. Bundle-visualizer as introspection tool, no hard budget enforcement

**Decision.** `rollup-plugin-visualizer` is configured in `vite.config.ts` to emit `dist/stats.html` on every production build. No CI check fails the build on size. Targets are advisory: ~200 KB gzip for the app shell, ~250 KB gzip for each route chunk.

**Rationale.**

- *Bundle visibility, not bundle policing.* The visualizer tells us what is actually in the bundle when we want to know; it does not block shipping when a feature pushes a chunk 10 KB over target. Hard budgets create churn-generating false positives in a small codebase where one `@mui/icons-material` import can move the number by 5 KB legitimately.
- *Real-device feel is the primary signal.* The thesis requires testing on a real iPhone and Android during Phase 2 (not Phase 6 — risk mitigation per PLAN.md). If the app feels snappy on the phone over mobile data, the bundle budget is implicitly met. If it doesn't, `stats.html` is the tool we already have ready.
- *The advisory targets are the web.dev mid-tier mobile ranges.* 200 KB gzip for initial JS is the web.dev recommendation for Time-to-Interactive under 5 s on throttled 4G. 250 KB per route chunk is a reasonable ceiling once code-splitting (§4) is in play. These are named so we know when something has drifted materially, not to gate merges.

**Implementation.** Phase 1 tail. `pnpm add -D rollup-plugin-visualizer`, added to Vite plugins with `{ filename: 'dist/stats.html', open: false, gzipSize: true, brotliSize: true }`. `dist/stats.html` is git-ignored. The targets are noted here; no script enforces them.

**Rejected alternatives.**

- *`size-limit` or `bundlewatch` in CI.* Enforces hard budgets at PR time. Useful for libraries and teams; over-scope for a solo-developer thesis where a single person can recognise regressions by eye.
- *Budget in `vite.config.ts` via Rollup's `output.experimentalMinChunkSize`.* Tweaks chunking heuristics, does not enforce totals. Not the right tool for the job.
- *No visualizer at all.* Leaves us blind when something does go wrong. The visualizer costs ~1 second of build time and is worth keeping.

**References.**

- `rollup-plugin-visualizer` — <https://github.com/btd/rollup-plugin-visualizer>
- web.dev, *Your first performance budget* — <https://web.dev/articles/performance-budgets-101>
- web.dev, *Fast load times* (mobile 4G baselines) — <https://web.dev/explore/fast>

---

## 7. UI library: MUI v7 with Emotion

**Decision.** MUI v7 (via its default Emotion engine) is the sole UI component library. No Tailwind, no shadcn/ui, no Radix primitives, no Chakra, no Mantine. Global styles go through MUI theme tokens; component-local styles through the `sx` prop. Icons come from `@mui/icons-material` with per-icon import paths to preserve tree-shaking.

**Rationale.**

- *Phases 4–5 depend on heavy components.* MUI ships a production-grade `<Autocomplete>`, `<DataGrid>` (via `@mui/x-data-grid`), date/time pickers (via `@mui/x-date-pickers`), and `<Slider>` that Phase 4 (simulation inputs, recommendation outputs) and Phase 5 (private point CRUD, booking tables, owner dashboard) will consume directly. Replicating these on shadcn/Radix primitives is real feature-scope work that the thesis timeline cannot absorb.
- *Theme consistency across heterogeneous surfaces.* The app mixes MapLibre (WebGL canvas), ECharts (Canvas-rendered), and conventional DOM. MUI's theme tokens (`theme.palette`, `theme.breakpoints`, `theme.typography`) flow into the ECharts theme (§3) and can be referenced from MapLibre style overlays. A single token system we already own beats two separate style systems kept aligned by hand.
- *Breakpoint ergonomics match the "responsive is mandatory" constraint.* The `sx={{ display: { xs: 'none', md: 'block' } }}` pattern is the tersest responsive API in the React ecosystem. The "test at 360 / 768 / 1280" rule in [frontend/CLAUDE.md](../frontend/CLAUDE.md) becomes trivial to honour.
- *Solo-dev timeline.* Switching UI libraries mid-thesis is a week of rework (forms, layouts, icons, theme). That week is worth more in Phases 3–4.

**Implementation.** Already scaffolded — [frontend/src/theme.ts](../frontend/src/theme.ts), Inter + JetBrains Mono via `@fontsource`. Convention: icons must be imported per-file (`import FooIcon from '@mui/icons-material/Foo'`), never via the barrel (`import { Foo } from '@mui/icons-material'`), because the barrel breaks tree-shaking and pulls megabytes of unused icons. Component-local colour and spacing via `sx`; anything shared goes into the theme.

**Rejected alternatives.**

- *shadcn/ui + Radix + Tailwind.* The dominant choice for new React apps in 2026 and arguably produces less "generic MUI" aesthetics out of the box. Disqualified here because (a) shadcn ships primitives, not the high-level composite components Phases 4–5 need (data grid, date pickers, virtualised autocomplete); rebuilding them on Radix primitives is weeks of work, (b) adding Tailwind alongside Emotion fragments the styling system across two mental models, (c) the timeline cost of switching mid-project is prohibitive even at parity. Recorded because the rejection is non-obvious and worth defending in the thesis.
- *Mantine.* Lighter than MUI, coherent design system, hooks-first. Disqualified on timeline grounds — the scaffold already uses MUI — and on the data-grid / date-picker argument (Mantine's equivalents are good but less battle-tested than MUI X).
- *Chakra.* Similar class to MUI; no meaningful differentiator for this project's use case. Momentum of the existing scaffold decides it.

**References.**

- MUI v7 documentation — <https://mui.com/material-ui/getting-started/>
- MUI X components (DataGrid, date pickers) — <https://mui.com/x/>
- Emotion (styling engine) — <https://emotion.sh/docs/introduction>

---

## 8. Forms policy: native actions for simple forms, react-hook-form + Zod for complex forms

**Decision.** Forms split by complexity:

- **Simple** (fewer than 5 static fields, no cross-field rules, no dependent fields): React Router v7 `<Form method="post">` + `action` + `useActionData` + MUI `<TextField>` with native HTML validation. Server errors echo into the form via `actionData`.
- **Complex** (5+ fields, any cross-field rule, any dependent / conditional fields): [`react-hook-form`](https://react-hook-form.com/) with [`@hookform/resolvers/zod`](https://github.com/react-hook-form/resolvers), [Zod](https://zod.dev/) schemas colocated per form, and TanStack Query `useMutation` (§11) for submission.

**Rationale.**

- *Phase 1 forms (login, register) are 2–3 fields with no cross-field logic.* RHF + Zod here would bypass React Router actions (RHF wants to own submission, actions want `FormData`), add two dependencies, and save at most a dozen lines. Bad trade.
- *Phase 4–5 forms are genuinely complex.* Private point creation has 8–12 fields with connector/price conditionals; booking creation has a cross-field time-window constraint; simulation has dependent fields (station → available connectors → price band). `useState`-per-field at that scale produces re-render waterfalls and unmaintainable validation code. RHF's uncontrolled-by-default refs and `formState.errors` are exactly the right abstraction.
- *Zod schemas are the single source of truth once adopted.* `z.infer<typeof Schema>` gives the form's TS type; `zodResolver(Schema)` gives runtime validation; the same schema can parse server error payloads back into field-level errors. Payoff compounds across forms.
- *Backend Pydantic still validates.* Frontend Zod is strictly UX — give users feedback before the round-trip, block submission when we already know it will fail. It is not a security boundary.
- *Spanish error messages colocate with schemas.* `z.string().min(1, 'Requerido')` places the Spanish copy next to the constraint. No translation file, no drift.

**Implementation.**

- Phase 1: no new deps. MUI `<TextField required type="email">`, React Router action returning `{ error: 'Mensaje en español' }` on failure. Password length ≥ 12 checked at the top of the action before hitting the API. Server-side error codes mapped to Spanish copy inside the action.
- Phase 4: `pnpm add react-hook-form zod @hookform/resolvers`. First consumers: simulation form, recommendation form. Convention: one `schema.ts` per form directory, import `zodResolver`, submit via TanStack Query `useMutation` so the mutation's `isPending` / `error` / `onSuccess` plugs into the form state.
- Phase 5: extend to private-point CRUD and booking forms. Cross-field validation via Zod's `.refine()` or `.superRefine()`.

**Rejected alternatives.**

- *RHF + Zod from Phase 1.* Over-engineered for 2–3 field auth forms and fights React Router actions (§9).
- *Formik.* Older, heavier per-field re-render model, weaker TS story than RHF + Zod. No reason to pick it in 2026.
- *Native form handling throughout.* Feasible for Phase 1 but becomes painful at 8+ fields; scaling RHF in once rather than retrofitting across six forms in Phase 5 is cheaper.
- *Yup, Joi, Valibot.* Yup and Joi predate the TS-first schema era; Valibot is TS-first and smaller than Zod but has less tooling momentum (adapters, community docs). Zod is the safe default for a thesis timeline — reconsider Valibot in a post-thesis polish pass.

**References.**

- React Hook Form — <https://react-hook-form.com/>
- Zod — <https://zod.dev/>
- `@hookform/resolvers` — <https://github.com/react-hook-form/resolvers>
- React Router v7 `Form` and `action` — <https://reactrouter.com/start/data/route-object#action>

---

## 9. Auth state via React Router v7 loaders and actions, no client-side store

**Decision.** Authentication state lives in a root-level `loader` that calls `GET /api/users/me`. All descendants read the user via `useRouteLoaderData('root')`. Login, register, and logout mutate via React Router `action`s that return `redirect(...)`, which triggers automatic revalidation of the root loader. `ProtectedRoute` and `AuthLayout` are small wrappers around the same `useRouteLoaderData` read, inverted for each direction of the gate. No Zustand, no Redux, no bespoke auth context, no `bootstrap()` effect, no client-side token handling.

**Rationale.**

- *Cookie is the session; there is no token to store.* Per [auth-decisions.md](auth-decisions.md) §6, the session is an HttpOnly cookie. The browser sends it automatically with `credentials: 'include'`; JavaScript cannot and must not read it. The only client-side question is "does the server currently consider me logged in?" — which is a fetch, not a state shape.
- *React Router v7's data APIs exist for exactly this.* `loader` runs on navigation, `action` runs on form submit, `useRouteLoaderData` exposes loader output tree-wide, and `redirect()` from an action auto-revalidates loaders downstream. A Zustand store on top of this layer would re-implement "re-run the loader after login/logout" — logic React Router already ships.
- *No `bootstrap()` footgun.* The previous Phase 1 plan had the app call `AuthStore.bootstrap()` on mount to seed the user. Getting this right across reloads, tab-wakes, and route transitions is subtly error-prone (double-fetches, races with protected-route redirects, stale user on navigation). The loader runs exactly when the framework needs it and never otherwise.
- *Simpler components.* `ProtectedRoute` becomes three lines (`useRouteLoaderData('root')` → `<Navigate to="/login" replace />` on null). `AuthLayout` mirrors it (`<Navigate to="/profile" replace />` when already authenticated). Login page has no manual `isSubmitting` — `useNavigation().state === 'submitting'` is free.
- *Progressive enhancement comes free.* React Router actions work with `<Form>` natively; if JS fails to load, submission still happens. Not thesis-critical but a welcome robustness property.

**Implementation.** Phase 1 Slice 1.

- **`src/auth/loaders.ts`** — `rootLoader()` calls `apiClient.GET('/api/users/me')` and returns `{ user: data ?? null }`. A 401 from the backend is an expected pre-login state, not an error.
- **`src/auth/actions.ts`** — `loginAction`, `registerAction`, `logoutAction`. Each returns either `{ error }` (for `useActionData`) or `redirect(...)`. On redirect, the root loader re-runs and the user is populated before the destination renders.
- **`src/components/ProtectedRoute.tsx`** — reads `useRouteLoaderData('root')`; when `user` is null it short-circuits to `<Navigate to="/login" replace />`. No effects, no state.
- **`src/layouts/AuthLayout.tsx`** — mirror pattern: if `useRouteLoaderData('root')` shows a user is already authenticated, `<Navigate to="/profile" replace />`; otherwise render a centred MUI container around `<Outlet />`. This keeps the "redirect away from login when already signed in" check on the *component* side (no extra network request) rather than a duplicate loader.
- **`src/router.tsx`** — root route has `id: 'root'` and `loader: rootLoader`. Two child branches: an `AuthLayout` branch for `/login` + `/register` (public); a `ProtectedRoute(RootLayout)` branch for the app shell (private). Logout is an action-only route (`POST /logout`).

**Rejected alternatives.**

- *Zustand store (original phase-1.md task 15).* Adds a dependency and a class of bugs (state-vs-server drift, missed revalidations) that the framework solves natively. The only thing Zustand would provide is cross-route reactivity to the user object, which `useRouteLoaderData` already provides.
- *React context + `useReducer`.* Same failure mode as Zustand, minus the dependency. Still requires `bootstrap()` and manual revalidation plumbing.
- *TanStack Query for the user object.* Workable, and the user object would get cache semantics for free, but duplicates React Router's loader machinery — two frameworks both claiming the same responsibility. TanStack Query is reserved for non-auth server state (§11).
- *`localStorage`-backed token cache.* Explicitly forbidden by [auth-decisions.md](auth-decisions.md) §6. The cookie is the session; writing auth state to `localStorage` is a regression.

**References.**

- React Router v7, *auth patterns* — <https://reactrouter.com/start/data/auth>
- `useRouteLoaderData` — <https://reactrouter.com/api/hooks/useRouteLoaderData>
- `redirect` from actions triggers revalidation — <https://reactrouter.com/start/data/actions>

---

## 10. Typed API client via `openapi-typescript` + `openapi-fetch`

**Decision.** The frontend's API surface is typed end-to-end by generating `src/api/schema.d.ts` from the backend's `/openapi.json` with [`openapi-typescript`](https://openapi-ts.dev/), and issuing requests through [`openapi-fetch`](https://openapi-ts.dev/openapi-fetch/) which consumes those types. No hand-written request/response types, no hand-maintained URL constants.

**Rationale.**

- *FastAPI already emits a perfect OpenAPI document.* `/openapi.json` is derived from Pydantic models and route signatures. Hand-translating those into TS interfaces is make-work with a drift risk.
- *`openapi-fetch` is a sub-KB typed wrapper around `fetch`.* It takes the generated `paths` type and constrains `GET` / `POST` / etc. method calls so path, query params, request body, and response shapes are all typed at call sites. No runtime transformation, no client code generation beyond the types themselves.
- *`tsc -b` becomes the contract check.* If the backend renames or removes a field, the frontend build fails at the consuming page, not at runtime in front of a user. This is the single highest-leverage protection against coupled-backend regressions.
- *No middleware layer needed for auth.* The cookie is the session; `credentials: 'include'` is set once on the client constructor.
- *Retries, caching, and dedup live in TanStack Query (§11), not in this client.* `openapi-fetch` stays thin — one responsibility.

**Implementation.** Phase 1 Slice 1, bundled into the task that previously created the hand-written `client.ts`.

```ts
// src/api/client.ts
import createClient from 'openapi-fetch'
import type { paths } from './schema'

export const apiClient = createClient<paths>({
  baseUrl: '',                // same-origin via Vite proxy in dev, Nginx in prod
  credentials: 'include',
})
```

- `package.json` gains `"gen:api": "openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts"`.
- Regenerate after every backend API change (`docker compose up backend db`, then `pnpm gen:api`); commit the resulting `schema.d.ts` so CI does not need the backend running to build.
- `src/api/types.ts` re-exports domain shapes (`User`, `UserCreate`, …) from `components['schemas']` so pages import from a stable barrel.
- [frontend/vite.config.ts](../frontend/vite.config.ts) gains `server.proxy: { '/api': 'http://backend:8000' }` so the dev server serves `/api/*` same-origin — the cookie stays first-party, no CORS, no `Access-Control-Allow-Credentials` gymnastics. `VITE_API_URL` is removed from [frontend/.env](../frontend/.env) and [frontend/.env.example](../frontend/.env.example) as now-unused.

**Rejected alternatives.**

- *Hand-written fetch wrapper with hand-written types (original phase-1.md task 15).* Works until the backend changes a field; the failure mode is silent runtime undefined-access rather than a type error.
- *`orval`.* Generates TanStack Query hooks in addition to types. Too opinionated for a slow-moving API and bundles a lot of generated code; `openapi-fetch` + manual `useQuery` is more controllable and of similar code volume.
- *`swagger-typescript-api`, `openapi-generator`.* Heavier code generators producing full client classes. Overkill when `openapi-fetch` covers the need in one import.
- *GraphQL + `graphql-codegen`.* Would provide stronger typing but requires rewriting the backend's REST surface. Not justified for Phase 1 scope.

**References.**

- `openapi-typescript` — <https://openapi-ts.dev/>
- `openapi-fetch` — <https://openapi-ts.dev/openapi-fetch/>
- FastAPI OpenAPI generation — <https://fastapi.tiangolo.com/tutorial/metadata/>

---

## 11. Server-state caching via TanStack Query from Phase 2

**Decision.** [TanStack Query](https://tanstack.com/query/latest) is introduced at the start of Phase 2 as the server-state layer for all non-auth data (REVE map points, ACN aggregations, simulation results, bookings, private points, owner dashboard). A single `<QueryClientProvider>` wraps the router in `main.tsx`. The `openapi-fetch` client from §10 is the transport.

**Rationale.**

- *Every feature from Phase 2 onward needs caching, dedup, and refetch semantics.* REVE points refreshed on a cadence; ACN aggregations that are expensive to recompute and benign to cache; simulation results the user revisits. Building these by hand around `useEffect` + `useState` is exactly the problem TanStack Query solves, and the DIY code grows with each feature.
- *The [frontend/CLAUDE.md](../frontend/CLAUDE.md) guidance "only if caching/dedup becomes painful" is the wrong default here.* By Phase 5, at least six screens will consume server state with non-trivial refetch needs. Introducing the library retroactively means rewriting each one.
- *Cost is ~13 KB gzip and one provider at the root.* Smaller than any single chart or map chunk.
- *Composes cleanly with §9's loader-based auth.* React Router loaders own authentication and initial page data; TanStack Query owns everything that benefits from cache / refetch / invalidate on top of that. No overlap in responsibility — the user object stays in the loader, map points belong in Query.
- *Mutations get progress, error, and success semantics for free.* `useMutation` returns `isPending` / `error` / `onSuccess` / `onError`; combined with the `react-hook-form` + Zod split from §8, Phase 4/5 forms become short.

**Implementation.** Phase 2.

- `pnpm add @tanstack/react-query`. Optional: `@tanstack/react-query-devtools` in dev.
- `<QueryClientProvider client={queryClient}>` wraps the router in [frontend/src/main.tsx](../frontend/src/main.tsx), inside `<ThemeProvider>` but outside `<SnackbarProvider>` (§12) so toast hooks can fire from query error boundaries.
- Default query options: `staleTime: 30_000` (most endpoints), `retry: 1`, `refetchOnWindowFocus: false` (PWA on mobile — don't refetch on every app-switch). Override per-hook as needed.
- Query key convention: `['points', filters]`, `['sessions', userId]`, `['analytics', 'energy', range]`. Nested by resource, then parameters.
- Invalidation: after a `useMutation`, `queryClient.invalidateQueries({ queryKey: [...] })` in `onSuccess`. Booking creation invalidates `['bookings']` and the relevant `['points', id]`.

**Rejected alternatives.**

- *Hand-rolled caching layer on top of `openapi-fetch`.* Becomes a small TanStack Query clone by Phase 5. No benefit.
- *SWR (Vercel).* Comparable feature set, smaller community tooling, slightly weaker mutation story. Not wrong, just less obviously the default in 2026.
- *Redux Toolkit Query.* Requires committing to Redux, which the project has rejected at the application state layer.
- *Deferring TanStack Query to "when it's painful" (previous CLAUDE.md guidance).* Painful means Phase 5, and by then six features have their own bespoke fetch logic to migrate. Predictable pain should be prevented, not absorbed.

**References.**

- TanStack Query — <https://tanstack.com/query/latest>
- `openapi-fetch` + TanStack Query — <https://openapi-ts.dev/openapi-fetch/examples#tanstack-query>

---

## 12. Toast notifications via notistack, action-return + imperative middleware split

**Decision.** User-facing transient notifications (session expired, logout success, generic server error) render through [`notistack`](https://notistack.com/) — a MUI-themed toast library wrapping MUI's `<Snackbar>`. A single `<SnackbarProvider maxSnack={3}>` sits inside `<ThemeProvider>` in `main.tsx`. Two usage patterns are allowed:

- **From React components:** `const { enqueueSnackbar } = useSnackbar()`.
- **From React Router actions or the `openapi-fetch` client (non-React contexts):** return a `{ toast: { message, variant } }` field from the action and dispatch via a small `useActionToast()` hook at the page level; or use notistack's imperative `enqueueSnackbar` export (v3+) for truly cross-cutting cases like a 401-interceptor middleware on the fetch client.

**Rationale.**

- *MUI-native theming.* The snackbar inherits the theme palette, typography, and spacing tokens without a second style system. No Tailwind/shadcn re-skin work.
- *Queueing is built in.* `maxSnack={3}` stacks and rotates; rolling this manually on top of MUI `<Snackbar>` is ~60 LOC of state and hook plumbing plus a testing burden the project does not need.
- *Actions are not React components.* React Router actions run outside the React tree, so `useSnackbar()` is unavailable inside them. Returning a toast instruction and letting a page-level hook dispatch it keeps the data flow one-way and avoids a module-level singleton for the common case.
- *Truly cross-cutting cases need the imperative escape hatch.* An `openapi-fetch` response middleware that catches 401s and surfaces "Tu sesión ha caducado" cannot return to a React component — the imperative `enqueueSnackbar` export is the right tool, reserved for this narrow usage.

**Implementation.** Phase 1 Slice 1.

- `pnpm add notistack`.
- Provider wired in [frontend/src/main.tsx](../frontend/src/main.tsx):

  ```tsx
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <SnackbarProvider
      maxSnack={3}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      autoHideDuration={4000}
    >
      <RouterProvider router={router} />
    </SnackbarProvider>
  </ThemeProvider>
  ```

- Auth-error copy is Spanish (app is Spanish-only, §13): `'Email o contraseña inválidos'`, `'Este email ya está registrado'`, `'Tu sesión ha caducado'`, `'Error del servidor'`.
- Form-scoped errors (login / register) render inline via MUI `<Alert>` from `useActionData` — no toast. Toasts are reserved for events *outside* a form context (session expiry mid-navigation, logout confirmation, unexpected 5xx).

**Rejected alternatives.**

- *Rolling a toast context on top of MUI `<Snackbar>`.* Reinvents the queue and the hook API. Every time.
- *`react-hot-toast` / `sonner`.* Smaller and excellent, but not MUI-themed; re-skinning to match the MUI theme eats any savings and introduces a second style system.
- *Always-imperative singleton (no action-return).* Works but couples action code to a hidden global and actions become harder to test.
- *Always action-return (no imperative).* Breaks the 401-interceptor case, which must fire from the fetch client rather than a page.

**References.**

- notistack — <https://notistack.com/>
- MUI Snackbar — <https://mui.com/material-ui/react-snackbar/>

---

## 13. i18n deferred: Spanish-only UI

**Decision.** The UI ships in Spanish only. No i18n library (`react-i18next`, `LinguiJS`, `FormatJS`) is introduced. All user-facing copy is written directly as Spanish string literals in the JSX / schema files.

**Rationale.**

- *Target audience is Spanish.* REVE is the Spanish charging network; the thesis defense is in Spanish; early users will be Spanish-speaking.
- *Cost of i18n is not trivial.* `react-i18next` adds ~20 KB, requires wrapping every user-visible string in `t('key')`, maintaining a JSON translation file, and enforcing the convention across reviews. For zero current user benefit.
- *Retrofit is linear and local.* If an English (or any second) market materialises post-thesis, the retrofit is a grep-over-strings plus a translation file — not an architectural change. Zod schemas colocate Spanish error messages today but can be parameterised later the same way the rest of the UI would be.

**Implementation.** No libraries, no `i18n.ts`. Copy lives where it renders.

**Rejected alternatives.**

- *`react-i18next` up-front.* Pure cost at this scale.
- *English-only UI.* Violates the "demo to a Spanish audience" acceptance criterion.

---

## Summary

| # | Decision | Phase |
| --- | --- | --- |
| 1 | MapLibre GL + `react-map-gl` | Phase 2 |
| 2 | MapTiler primary; self-hosted Protomaps documented as fallback | Phase 2 (/ Phase 6 opt-in) |
| 3 | Apache ECharts via `echarts-for-react`, tree-shaken | Phase 3 |
| 4 | Route-based code splitting via React Router v7 `lazy` | Phase 2 onward |
| 5 | Lighthouse audits at Phase 1 / 2 / 3 / 6 milestones, not CI | all phases |
| 6 | Bundle-visualizer available, advisory targets, no CI gate | Phase 1 tail |
| 7 | MUI v7 with Emotion; shadcn/Tailwind and Mantine rejected | Phase 1 onward |
| 8 | Native actions for simple forms; react-hook-form + Zod for complex forms | Phase 1 / Phase 4 |
| 9 | Auth state via React Router loaders and actions; no client-side store | Phase 1 |
| 10 | Typed API client via `openapi-typescript` + `openapi-fetch` | Phase 1 |
| 11 | TanStack Query for non-auth server state | Phase 2 onward |
| 12 | Notistack for toasts; action-return + imperative middleware split | Phase 1 |
| 13 | i18n deferred; Spanish-only UI | all phases |

Decisions are deliberately scoped to what the thesis actually ships; anything cheaper (Lighthouse CI, hard bundle gates, SSR, i18n) is deferred and documented rather than absent.
