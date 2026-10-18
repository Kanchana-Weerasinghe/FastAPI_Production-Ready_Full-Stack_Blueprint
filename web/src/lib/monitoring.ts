import * as Sentry from "@sentry/react";

import { apiBaseUrl } from "./config";

/**
 * Frontend error tracking and Real User Monitoring (Sentry).
 *
 * Enabled only when VITE_SENTRY_DSN is set at build time. Captures unhandled errors, React render
 * errors (via the root ErrorBoundary), page-load/navigation performance and Core Web Vitals
 * (LCP, INP, CLS), tagged with the release. Distributed tracing headers are only sent to our API.
 * No PII: default PII collection is off and session replay is not enabled.
 */
export const initMonitoring = (): void => {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;
  const apiOrigin = apiBaseUrl() || window.location.origin;
  Sentry.init({
    dsn,
    release: import.meta.env.VITE_APP_VERSION,
    environment: import.meta.env.MODE,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
    tracePropagationTargets: [apiOrigin],
    sendDefaultPii: false,
  });
};

export { Sentry };
