import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  useCreateTodo,
  useDeleteTodo,
  useRemoveAttachment,
  useToggleArchiveTodo,
  useUpdateTodo,
} from "@/hooks/mutations/todos";

import { createWrapper } from "../../../test_utils";

describe("useCreateTodo", () => {
  it("is idle on initial render", () => {
    const { result } = renderHook(() => useCreateTodo(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(false);
    expect(result.current.isSuccess).toBe(false);
  });

  it("succeeds when a valid todo is submitted", async () => {
    const { result } = renderHook(() => useCreateTodo(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ title: "Buy groceries" });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useUpdateTodo", () => {
  it("succeeds when updating an existing todo", async () => {
    const { result } = renderHook(() => useUpdateTodo("todo-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ title: "Updated title", isCompleted: true });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useDeleteTodo", () => {
  it("is idle on initial render", () => {
    const { result } = renderHook(() => useDeleteTodo(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isPending).toBe(false);
  });

  it("succeeds when deleting a todo by ID", async () => {
    const { result } = renderHook(() => useDeleteTodo(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("todo-1");

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useToggleArchiveTodo", () => {
  it("succeeds when toggling archive status", async () => {
    const { result } = renderHook(() => useToggleArchiveTodo(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("todo-1");

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useRemoveAttachment", () => {
  it("succeeds when removing an attachment by file ID", async () => {
    const { result } = renderHook(() => useRemoveAttachment("todo-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate("att-1");

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});
