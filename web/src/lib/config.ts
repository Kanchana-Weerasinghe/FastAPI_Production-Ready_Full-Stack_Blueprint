/**
 * Base URL of the API.
 *
 * - `VITE_API_URL` set (e.g. "https://api.example.com") → cross-origin API.
 * - Set but empty → same origin (production behind one ingress: "/v2/..." requests).
 * - Unset in development → the local FastAPI dev server.
 */
export const apiBaseUrl = (): string =>
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8000" : "");
