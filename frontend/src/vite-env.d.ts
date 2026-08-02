/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  /** Git tag the bundle was built from; `dev` outside a CD build. */
  readonly VITE_APP_VERSION: string
}
