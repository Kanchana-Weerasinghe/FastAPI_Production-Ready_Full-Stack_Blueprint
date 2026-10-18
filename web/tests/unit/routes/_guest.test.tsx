import { describe, expect, it, vi } from "vitest";

import { fetchUser } from "@/hooks/queries/user";
import { Route as GuestRoute } from "@/routes/_guest/route";
import { authStore } from "@/store/auth.store";

vi.mock("@/hooks/queries/user", () => ({
  fetchUser: vi.fn(),
}));

vi.mock("@/lib/query", () => ({
  queryClient: {
    fetchQuery: vi.fn(async ({ queryFn }) => {
      return queryFn();
    }),
  },
}));

vi.mock("@/store/auth.store", () => {
  const store = { state: { user: null } };
  return {
    authStore: store,
    setAuth: vi.fn((user) => {
      store.state.user = user;
    }),
  };
});

describe("Guest Route", () => {
  it("redirects to /todos when user is authenticated", async () => {
    authStore.state.user = { id: "1" } as never;

    try {
      await GuestRoute.options.beforeLoad!({} as never);
      expect.fail("Should have thrown a redirect");
    } catch (e) {
      expect(e).toBeDefined();
    }
  });

  it("does not redirect when user is not authenticated and fetch fails", async () => {
    authStore.state.user = null;
    vi.mocked(fetchUser).mockRejectedValueOnce(new Error("unauthorized"));

    await GuestRoute.options.beforeLoad!({} as never);
    expect(authStore.state.user).toBeNull();
  });

  it("redirects to /todos when user is not authenticated but fetch succeeds", async () => {
    authStore.state.user = null;
    vi.mocked(fetchUser).mockResolvedValueOnce({ id: "2" } as never);

    try {
      await GuestRoute.options.beforeLoad!({} as never);
      expect.fail("Should have thrown a redirect");
    } catch (e) {
      expect(authStore.state.user).toEqual({ id: "2" });
      expect(e).toBeDefined();
    }
  });
});
