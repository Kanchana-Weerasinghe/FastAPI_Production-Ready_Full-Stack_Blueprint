import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { fetchUser, useUser } from "@/hooks/queries/user";

import { createWrapper } from "../../../test_utils";

describe("fetchUser", () => {
  it("fetches and returns a validated user object", async () => {
    const user = await fetchUser();

    expect(user.id).toBe("user-1");
    expect(user.email).toBe("test@example.com");
    expect(user.username).toBe("testuser");
  });

  it("throws when the server returns an invalid user shape", async () => {
    const { server } = await import("../../../mocks/server");
    const { http, HttpResponse } = await import("msw");

    server.use(
      http.get("http://localhost:8000/v2/user/me", () =>
        HttpResponse.json({ id: "user-1" }),
      ),
    );

    await expect(fetchUser()).rejects.toThrow();
  });
});

describe("useUser", () => {
  it("is in loading state initially", () => {
    const { result } = renderHook(() => useUser(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(true);
  });

  it("fetches and returns the authenticated user", async () => {
    const { result } = renderHook(() => useUser(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.email).toBe("test@example.com");
    expect(result.current.data?.username).toBe("testuser");
  });
});
