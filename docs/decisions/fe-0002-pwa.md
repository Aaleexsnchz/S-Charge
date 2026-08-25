---
id: fe-0002
status: accepted
phase: 1
date: 2026-06
---

# fe-0002: Ship the frontend as an installable Progressive Web App

**Decision.** The frontend ships as a Progressive Web App: web app manifest + service worker, installable on iOS Safari ("Add to Home Screen") and Android / desktop Chrome (native install prompt). No App Store, no Play Store, no native shell. Implemented via [`vite-plugin-pwa`](https://vite-pwa-org.netlify.app/) (Workbox under the hood).

**Rationale.** The user-facing target is an EV driver standing next to a charging point on a phone. A PWA delivers the home-screen icon, standalone window (no browser chrome), and offline-capable shell that make the product feel like an app, while keeping a single codebase, a single deploy, and a single QA matrix. Native iOS + Android development is out of scope for a solo thesis — two app-store reviews, two build pipelines, two crash-reporting stacks, and the ongoing tax of running `react-native` upgrades through both ecosystems. None of that pays academic dividends for a thesis whose contribution is the application itself.

Concrete affordances the PWA layer unlocks for later phases:

- *Offline catalogue.* The REVE-seeded charging-point set is static between seed runs; the service worker can cache it for the map's cold-start view.
- *Installability with first-party cookies.* The same-origin session cookie ([auth-0002](auth-0002-cookie-session.md)) keeps working in the installed standalone window — no special token-handoff dance.
- *Background sync.* A session confirmation made while offline could queue in the service worker and replay when connectivity returns — available to [charging sessions](../features/sessions.md) because the PWA shell exists.

**Implementation.** `vite-plugin-pwa` configured in `frontend/vite.config.ts` with a generated manifest, Workbox-based precaching of the app shell, and iOS-specific `<link rel="apple-touch-icon">` / status-bar meta tags in `frontend/index.html`. Icons generated from a single source SVG via `@vite-pwa/assets-generator` (`pnpm gen:pwa-assets`). Manual smoke test: Chrome install prompt fires, iOS Safari "Add to Home Screen" launches standalone with the correct splash. Caching is Workbox's `generateSW` precache of the built JS, CSS and `index.html` plus the manifest icons, with two runtime routes on top: `/api/points/map` stale-while-revalidate (the catalogue only moves when the REVE seed runs, and the endpoint is public, so nothing user-scoped lands in the cache) and same-origin fonts cache-first (cached on demand rather than precached, so only the subsets the browser asks for are stored). Everything else is network-only by design: prices track the hourly PVPC and a stale price read as current is worse than a visible failure, which is the same premise as [be-0004](be-0004-session-is-the-quote-it-accepted.md). The map's basemap is a third-party style URL, so the map itself does not work offline regardless.

**Rejected alternatives.**

- *React Native (Expo).* Real native UI, real native APIs — and a second build pipeline, two app-store accounts, two review queues, and a separate crash-reporting story. Disproportionate for a thesis with one developer.
- *Capacitor / Tauri-wrapped web app.* A web app inside a native shell. Solves App Store presence and unlocks deeper native APIs, but inherits the app-store overhead without the native-UI payoff for a webview-based UI. No thesis benefit.
- *Plain web app, no PWA.* Cuts the service worker and the manifest, loses installability and the offline-cache opportunity that the catalogue is a natural fit for. The incremental cost of `vite-plugin-pwa` is small enough that "just ship a website" is not worth the loss.

**References.**

- `vite-plugin-pwa` documentation
- Workbox documentation
- web.dev — *Progressive Web Apps*
- Apple — *Configuring Web Applications*
