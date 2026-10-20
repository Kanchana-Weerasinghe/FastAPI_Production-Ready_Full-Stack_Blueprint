import { describe, expect, it } from "vitest";

import {
  findTodoParamsSchema,
  todoListResponseSchema,
  todoResponseSchema,
  todoSchema,
  todoUpdateSchema,
} from "@/models/todo";

describe("todoSchema", () => {
  it("accepts a valid title", () => {
    const result = todoSchema.safeParse({ title: "Buy groceries" });
    expect(result.success).toBe(true);
  });

  it("rejects an empty title", () => {
    const result = todoSchema.safeParse({ title: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].message).toBe("Title is missing");
  });

  it("rejects a title exceeding 100 characters", () => {
    const result = todoSchema.safeParse({ title: "a".repeat(101) });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].message).toBe(
      "Must be less than 100 characters",
    );
  });

  it("accepts an optional description", () => {
    const result = todoSchema.safeParse({
      title: "Test",
      description: "Some notes",
    });
    expect(result.success).toBe(true);
  });
});

describe("todoUpdateSchema", () => {
  it("accepts isCompleted field in addition to base fields", () => {
    const result = todoUpdateSchema.safeParse({
      title: "Updated",
      isCompleted: true,
    });
    expect(result.success).toBe(true);
  });

  it("allows isCompleted to be omitted", () => {
    const result = todoUpdateSchema.safeParse({ title: "Updated" });
    expect(result.success).toBe(true);
  });
});

describe("todoResponseSchema", () => {
  const validTodo = {
    id: "uuid-1",
    userId: "user-1",
    title: "Test Todo",
    isCompleted: false,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  };

  it("parses a valid todo response", () => {
    const result = todoResponseSchema.safeParse(validTodo);
    expect(result.success).toBe(true);
  });

  it("rejects when required fields are missing", () => {
    const result = todoResponseSchema.safeParse({ title: "Missing fields" });
    expect(result.success).toBe(false);
  });
});

describe("todoListResponseSchema", () => {
  it("parses a valid list response", () => {
    const result = todoListResponseSchema.safeParse({
      founds: [
        {
          id: "1",
          title: "Item",
          isCompleted: false,
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      ],
      searchOptions: { totalCount: 1 },
    });
    expect(result.success).toBe(true);
  });
});

describe("findTodoParamsSchema", () => {
  it("accepts all optional fields", () => {
    const result = findTodoParamsSchema.safeParse({
      title: "test",
      page: 1,
      pageSize: 10,
      isActive: true,
    });
    expect(result.success).toBe(true);
  });

  it("accepts an empty object (all fields optional)", () => {
    const result = findTodoParamsSchema.safeParse({});
    expect(result.success).toBe(true);
  });
});
