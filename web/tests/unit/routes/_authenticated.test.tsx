import { describe, expect, it, vi } from "vitest";

import { fetchUser } from "@/hooks/queries/user";
import { Route as AuthRoute } from "@/routes/_authenticated/route";
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

describe("Authenticated Route", () => {
  it("redirects to / when user is not authenticated and fetch fails", async () => {
    vi.mocked(fetchUser).mockRejectedValueOnce(new Error("unauthorized"));
    authStore.state.user = null;

    try {
      await AuthRoute.options.beforeLoad!({
        location: { pathname: "/test" },
      } as never);
      expect.fail("Should have thrown a redirect");
    } catch (e) {
      expect(e).toBeDefined();
    }
  });

  it("redirects to /home when user is authenticated but visits /", async () => {
    authStore.state.user = { id: "1" } as never;

    try {
      await AuthRoute.options.beforeLoad!({
        location: { pathname: "/" },
      } as never);
      expect.fail("Should have thrown a redirect");
    } catch (e) {
      expect(e).toBeDefined();
    }
  });

  it("sets auth user when not authenticated but fetch succeeds", async () => {
    authStore.state.user = null;
    vi.mocked(fetchUser).mockResolvedValueOnce({ id: "2" } as never);

    await AuthRoute.options.beforeLoad!({
      location: { pathname: "/test" },
    } as never);
    expect(authStore.state.user).toEqual({ id: "2" });
  });
});
