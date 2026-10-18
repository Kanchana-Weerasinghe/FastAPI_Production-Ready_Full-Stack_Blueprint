import { describe, expect, it } from "vitest";

import {
  authStore,
  clearAuth,
  selectIsAuthenticated,
  setAuth,
} from "@/store/auth.store";

describe("auth.store", () => {
  it("initializes with null user", () => {
    expect(authStore.state.user).toBeNull();
    expect(selectIsAuthenticated(authStore.state)).toBe(false);
  });

  it("sets auth user", () => {
    const user = { id: "1", email: "test@test.com" } as never;
    setAuth(user);
    expect(authStore.state.user).toEqual(user);
    expect(selectIsAuthenticated(authStore.state)).toBe(true);
  });

  it("clears auth user", () => {
    clearAuth();
    expect(authStore.state.user).toBeNull();
    expect(selectIsAuthenticated(authStore.state)).toBe(false);
  });
});
