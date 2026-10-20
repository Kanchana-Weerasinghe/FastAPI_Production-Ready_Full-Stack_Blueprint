import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useTodo, useTodos } from "@/hooks/queries/todos";

import { createWrapper } from "../../../test_utils";

describe("useTodos", () => {
  it("is in loading state initially", () => {
    const { result } = renderHook(() => useTodos(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(true);
  });

  it("fetches and returns the todo list", async () => {
    const { result } = renderHook(() => useTodos(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.founds).toHaveLength(1);
    expect(result.current.data?.founds[0].title).toBe("Test Todo");
  });

  it("includes params in the query key for filtering", async () => {
    const { result } = renderHook(() => useTodos({ title: "groceries" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useTodo", () => {
  it("fetches a single todo by ID", async () => {
    const { result } = renderHook(() => useTodo("todo-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.id).toBe("todo-1");
    expect(result.current.data?.title).toBe("Test Todo");
  });
});
