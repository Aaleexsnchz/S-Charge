import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// Inside Docker the backend is reachable by service name; host-side runs
// (pnpm preview for Lighthouse) override via VITE_PROXY_TARGET.
const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: false,
      workbox: {
        // The OAuth callback is a top-level navigation to /api/*. Without this
        // the navigation fallback answers it from the precache, so the backend
        // never sets the session cookie and the SPA renders its 404 instead.
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            // The catalogue only changes when the REVE seed runs, so a stale
            // read is worth an instant cold-start map. Prices are never served
            // from a cache: a stale price read as current is worse than an error.
            urlPattern: ({ url, sameOrigin }) => sameOrigin && url.pathname === '/api/points/map',
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'points-map',
              expiration: { maxEntries: 1, maxAgeSeconds: 60 * 60 * 24 * 7 },
              cacheableResponse: { statuses: [200] },
            },
          },
          {
            // Cached at runtime rather than precached so only the subsets the
            // browser actually asks for are stored; @fontsource ships 28 files
            // per build and the app renders one of them.
            urlPattern: ({ request, sameOrigin }) => sameOrigin && request.destination === 'font',
            handler: 'CacheFirst',
            options: {
              cacheName: 'fonts',
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
              cacheableResponse: { statuses: [200] },
            },
          },
        ],
      },
      devOptions: {
        enabled: true,
        type: 'module',
        // In dev there is no build output to precache, so workbox warns that its
        // glob matched nothing on every restart. Nothing to fix, just noise.
        suppressWarnings: true,
      },
      manifest: {
        name: 'S-Charge',
        short_name: 'S-Charge',
        description: 'Gestión de puntos de carga eléctrica',
        lang: 'es',
        theme_color: '#7FE7C4',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: '/pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          {
            src: '/maskable-icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': proxyTarget,
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    proxy: {
      '/api': proxyTarget,
    },
  },
})
