import "./index.css";

import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { createRouter, Navigate, RouterProvider } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { ErrorFallback } from "./components/common/ErrorFallback";
import { initMonitoring, Sentry } from "./lib/monitoring";
import { queryClient } from "./lib/query";
import { routeTree } from "./routeTree.gen";

initMonitoring();

const router = createRouter({
  routeTree,
  // Route components are code-split automatically (autoCodeSplitting in vite.config.ts) and
  // preloaded on link hover/focus.
  defaultPreload: "intent",
  defaultNotFoundComponent: () => {
    return <Navigate to="/" />;
  },
  // Errors thrown while loading/rendering a route render this instead of a blank page.
  defaultErrorComponent: ({ error, reset }) => {
    Sentry.captureException(error);
    return <ErrorFallback error={error} reset={reset} />;
  },
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

const rootElement = document.getElementById("root")!;
if (!rootElement.innerHTML) {
  const root = createRoot(rootElement, {
    // React 19 error hooks: report errors React caught or could not recover from.
    onUncaughtError: Sentry.reactErrorHandler(),
    onCaughtError: Sentry.reactErrorHandler(),
  });
  root.render(
    <StrictMode>
      <Sentry.ErrorBoundary
        fallback={({ error, resetError }) => (
          <ErrorFallback error={error} reset={resetError} />
        )}
      >
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
          {import.meta.env.DEV && (
            <>
              <TanStackRouterDevtools router={router} />
              <ReactQueryDevtools initialIsOpen={false} />
            </>
          )}
        </QueryClientProvider>
      </Sentry.ErrorBoundary>
    </StrictMode>,
  );
}
