import { Button } from "./Button";

interface ErrorFallbackProps {
  error?: unknown;
  reset?: () => void;
}

/**
 * Shown when rendering fails (root error boundary and router error component) instead of a blank
 * page. The error itself is reported to monitoring; users only see a recovery path.
 */
export function ErrorFallback({ reset }: ErrorFallbackProps) {
  return (
    <main
      role="alert"
      className="min-h-screen flex flex-col items-center justify-center gap-4 p-6 bg-brand-100 text-center"
    >
      <h1 className="text-2xl font-bold text-brand-600">
        Something went wrong
      </h1>
      <p className="text-gray-700 max-w-md">
        An unexpected error occurred. Try again, or reload the page if the
        problem persists.
      </p>
      <div className="flex gap-3">
        {reset && <Button onClick={reset}>Try again</Button>}
        <Button variant="outline" onClick={() => window.location.assign("/")}>
          Go home
        </Button>
      </div>
    </main>
  );
}
