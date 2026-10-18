import axios, { type InternalAxiosRequestConfig } from "axios";

import { apiBaseUrl } from "./config";

/**
 * Pre-configured Axios instance for all API communication.
 *
 * Features:
 * - Automatic baseURL selection from environment variables.
 * - `withCredentials: true` so the HttpOnly session cookies are sent.
 * - CSRF protection: echoes the readable `csrf_token` cookie in the `X-CSRF-Token`
 *   header on every request (double-submit), as required by the API for unsafe methods.
 * - Silent session refresh: when a request fails with 401 (short-lived access token
 *   expired), calls `/v1/auth/refresh` once and retries the request. Concurrent 401s
 *   share a single refresh call.
 */
const client = axios.create({
  baseURL: apiBaseUrl(),
  withCredentials: true,
  xsrfCookieName: "csrf_token",
  xsrfHeaderName: "X-CSRF-Token",
  withXSRFToken: true,
  headers: {
    "Content-Type": "application/json",
  },
});

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

let refreshInFlight: Promise<void> | null = null;

const refreshSession = (): Promise<void> => {
  refreshInFlight ??= client
    .post("/v1/auth/refresh")
    .then(() => undefined)
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
};

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as RetriableConfig | undefined;
    const isAuthEndpoint = original?.url?.startsWith("/v1/auth/") ?? false;
    if (
      error.response?.status === 401 &&
      original &&
      !original._retried &&
      !isAuthEndpoint
    ) {
      original._retried = true;
      try {
        await refreshSession();
      } catch {
        return Promise.reject(error);
      }
      return client(original);
    }
    return Promise.reject(error);
  },
);

export default client;
