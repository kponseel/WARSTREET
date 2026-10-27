/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** The deployed commit (deploy-pages.yml), shown on #/debug. */
  readonly VITE_APP_COMMIT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
