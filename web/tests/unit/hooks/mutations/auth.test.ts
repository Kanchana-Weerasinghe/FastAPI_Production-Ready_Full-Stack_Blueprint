import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useSignIn, useSignOut, useSignUp } from "@/hooks/mutations/auth";
import { authStore, setAuth } from "@/store/auth.store";

import { createWrapper } from "../../../test_utils";

describe("useSignIn", () => {
  it("returns a mutation in idle state initially", () => {
    const { result } = renderHook(() => useSignIn(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(false);
    expect(result.current.isSuccess).toBe(false);
  });

  it("succeeds when valid credentials are submitted", async () => {
    const { result } = renderHook(() => useSignIn(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ email: "user@example.com", password: "pass1234" });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("fails when the server returns an error", async () => {
    const { server } = await import("../../../mocks/server");
    const { http, HttpResponse } = await import("msw");

    server.use(
      http.post("http://localhost:8000/v1/auth/signin", () =>
        HttpResponse.json({ detail: "Invalid credentials" }, { status: 401 }),
      ),
    );

    const { result } = renderHook(() => useSignIn(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ email: "bad@example.com", password: "wrongpass" });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe("useSignUp", () => {
  it("returns a mutation in idle state initially", () => {
    const { result } = renderHook(() => useSignUp(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(false);
  });

  it("succeeds when valid registration data is submitted", async () => {
    const { result } = renderHook(() => useSignUp(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ email: "new@example.com", password: "pass1234" });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useSignOut", () => {
  it("clears the local auth state after the server ends the session", async () => {
    setAuth({
      id: "user-1",
      email: "test@example.com",
      username: "testuser",
      role: "user",
      emailVerified: true,
      mfaEnabled: false,
    });
    const { result } = renderHook(() => useSignOut(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(authStore.state.user).toBeNull();
  });

  it("still clears the local auth state when the request fails", async () => {
    const { server } = await import("../../../mocks/server");
    const { http, HttpResponse } = await import("msw");
    server.use(
      http.post("http://localhost:8000/v1/auth/signout", () =>
        HttpResponse.json({}, { status: 500 }),
      ),
    );
    setAuth({
      id: "user-1",
      email: "test@example.com",
      username: "testuser",
      role: "user",
      emailVerified: true,
      mfaEnabled: false,
    });
    const { result } = renderHook(() => useSignOut(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(authStore.state.user).toBeNull();
  });
});
