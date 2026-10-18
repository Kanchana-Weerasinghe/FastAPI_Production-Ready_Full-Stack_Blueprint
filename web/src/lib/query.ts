import { QueryClient } from "@tanstack/react-query";
import axios from "axios";

/**
 * Global TanStack Query Client configuration.
 *
 * Rules:
 * - Stale and Garbage Collection time set to 5 minutes to reduce server load.
 * - Selective retry logic: Only retries once, and only for 5xx server errors.
 * - Window focus refetching is disabled to prevent flickering on tab switch.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 5,
      retry: (failureCount, error) => {
        if (failureCount >= 1) return false;
        if (
          axios.isAxiosError(error) &&
          error.response?.status &&
          error.response.status >= 500
        ) {
          return true;
        }
        return false;
      },
      refetchOnWindowFocus: false,
    },
  },
});
