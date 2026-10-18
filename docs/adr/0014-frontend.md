# 0014. Frontend: secure sessions, resilience, monitoring, budgets and accessibility

- Status: Accepted
- Date: 2026-10-16

## Context

The SPA needs to work with short-lived cookie sessions and CSRF protection, must not show a blank page on errors, has to be observable in real browsers, and must stay fast and accessible as it grows.

## Decision

- **Auth**: tokens live only in HttpOnly cookies (never `localStorage`). Axios echoes the `csrf_token` cookie as `X-CSRF-Token` and transparently calls `/v1/auth/refresh` once on 401 (`src/lib/client.ts`). API errors are RFC 9457 documents; UI messages come from `detail`, logic branches on `code` (`src/lib/problem.ts`).
- **Resilience**: a root `Sentry.ErrorBoundary` plus the router's `defaultErrorComponent` render `ErrorFallback` with a recovery path.
- **Code splitting**: TanStack Router `autoCodeSplitting` (one chunk per route) with intent preloading; dev tools are excluded from production bundles.
- **Monitoring / RUM**: Sentry (opt-in via `VITE_SENTRY_DSN`) for errors, page-load/navigation traces and Core Web Vitals, tagged with the release; trace headers only to our API; no PII or session replay by default.
- **Security headers**: strict CSP without inline scripts (`script-src 'self'`), HSTS, frame denial, `nosniff`, Permissions-Policy, set by the web image's nginx. Hashed assets are cached immutably; `index.html` is never cached. Serve assets through a CDN in front of the web service if global latency matters.
- **Budgets**: Lighthouse CI fails the build below performance 0.9 / accessibility 0.95, LCP > 2.5 s, CLS > 0.1, TBT > 300 ms or JS > 350 kB.
- **Accessibility**: WCAG 2.1 AA as the standard. `eslint-plugin-jsx-a11y` in lint, axe-core checks in Playwright, semantic landmarks and labelled inputs in shared components.
- **i18n** (when needed): adopt `react-i18next` or Lingui, keep strings out of components from the first translated screen, format dates/numbers with `Intl`, and send `Accept-Language` to the API so emails and errors can be localised.

## Consequences

- Building one image per API origin is required when the API is cross-origin (`VITE_API_URL` is inlined at build time); same-origin deployments (the default Helm setup) avoid it.
- The CSP must be extended deliberately when adding third-party scripts, fonts or APIs.
