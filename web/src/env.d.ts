/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API origin; empty = same origin (served behind the same ingress). */
  readonly VITE_API_URL?: string;
  /** Enables Sentry error tracking + real-user monitoring when set. */
  readonly VITE_SENTRY_DSN?: string;
  /** Release identifier injected at build time (git SHA / version). */
  readonly VITE_APP_VERSION?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
