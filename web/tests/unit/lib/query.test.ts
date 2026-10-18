import axios from "axios";
import { describe, expect, it } from "vitest";

import { queryClient } from "@/lib/query";

describe("queryClient configuration", () => {
  const retryFn = queryClient.getDefaultOptions().queries?.retry as (
    failureCount: number,
    error: unknown,
  ) => boolean;

  it("exports a configured QueryClient", () => {
    expect(queryClient).toBeDefined();
    const options = queryClient.getDefaultOptions().queries;
    expect(options?.staleTime).toBe(300000);
    expect(options?.gcTime).toBe(300000);
    expect(options?.refetchOnWindowFocus).toBe(false);
  });

  describe("retry logic", () => {
    it("does not retry if failureCount is >= 1", () => {
      const error = new Error("Network Error");
      expect(retryFn(1, error)).toBe(false);
      expect(retryFn(5, error)).toBe(false);
    });

    it("does not retry for non-Axios errors", () => {
      const error = new Error("Standard JS Error");
      expect(retryFn(0, error)).toBe(false);
    });

    it("does not retry for Axios errors with status < 500", () => {
      const error = new axios.AxiosError(
        "Not Found",
        "404",
        undefined,
        undefined,
        {
          status: 404,
          statusText: "Not Found",
          data: {},
          headers: {},
          config: {} as never,
        },
      );
      expect(retryFn(0, error)).toBe(false);
    });

    it("retries for Axios errors with status >= 500", () => {
      const error = new axios.AxiosError(
        "Server Error",
        "500",
        undefined,
        undefined,
        {
          status: 500,
          statusText: "Server Error",
          data: {},
          headers: {},
          config: {} as never,
        },
      );
      expect(retryFn(0, error)).toBe(true);

      const error503 = new axios.AxiosError(
        "Service Unavailable",
        "503",
        undefined,
        undefined,
        {
          status: 503,
          statusText: "Service Unavailable",
          data: {},
          headers: {},
          config: {} as never,
        },
      );
      expect(retryFn(0, error503)).toBe(true);
    });

    it("does not retry if response is undefined", () => {
      const error = new axios.AxiosError("Network Error");
      expect(retryFn(0, error)).toBe(false);
    });
  });
});
