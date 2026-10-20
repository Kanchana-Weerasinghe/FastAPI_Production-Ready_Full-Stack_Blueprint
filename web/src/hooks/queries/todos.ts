import { keepPreviousData, useQuery } from "@tanstack/react-query";

import client from "../../lib/client";
import type { FindTodoParams, Todo, TodoListResponse } from "../../models/todo";

/**
 * Hook to fetch a paginated and filtered list of todos.
 * Uses 'keepPreviousData' to maintain UI stability during pagination.
 *
 * @param params - Search and pagination filters (title, isActive, page, etc.).
 * @returns A query object containing the TodoListResponse.
 */
export const useTodos = (params?: FindTodoParams) => {
  return useQuery({
    queryKey: ["todos", params],
    queryFn: async () => {
      const response = await client.get<TodoListResponse>("/v2/todos/", {
        params,
      });
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

/**
 * Hook to fetch the full details of a single todo by ID.
 *
 * @param todoId - The unique identifier of the todo.
 * @returns A query object containing the Todo data.
 */
export const useTodo = (todoId: string) => {
  return useQuery({
    queryKey: ["todos", todoId],
    queryFn: async () => {
      const response = await client.get<Todo>(`/v2/todos/${todoId}`);
      return response.data;
    },
    enabled: !!todoId,
  });
};
