import { useMutation, useQueryClient } from "@tanstack/react-query";

import client from "../../lib/client";
import type { TodoFormValues, TodoUpdate } from "../../models/todo";

/**
 * Hook to create a new todo.
 * Invalidates 'todos' query on success.
 *
 * @returns A mutation object for todo creation.
 */
export const useCreateTodo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TodoFormValues) => {
      await client.post("/v2/todos/", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos"] });
    },
  });
};

/**
 * Hook to update an existing todo by ID.
 * Invalidates both the list and the specific todo detail queries.
 *
 * @param todoId - The unique identifier of the todo.
 * @returns A mutation object for todo updates.
 */
export const useUpdateTodo = (todoId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<TodoUpdate>) => {
      await client.patch(`/v2/todos/${todoId}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos"] });
      queryClient.invalidateQueries({ queryKey: ["todos", todoId] });
    },
  });
};

/**
 * A generic hook to update any todo, useful for list-level actions (e.g., toggling completion).
 *
 * @returns A mutation object that accepts { todoId, data }.
 */
export const useUpdateTodoGeneric = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      todoId,
      data,
    }: {
      todoId: string;
      data: Partial<TodoUpdate>;
    }) => {
      await client.patch(`/v2/todos/${todoId}`, data);
    },
    onSuccess: (_, { todoId }) => {
      queryClient.invalidateQueries({ queryKey: ["todos"] });
      queryClient.invalidateQueries({ queryKey: ["todos", todoId] });
    },
  });
};

/**
 * Hook to toggle the archived status of a todo.
 *
 * @returns A mutation object for archiving/unarchiving.
 */
export const useToggleArchiveTodo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (todoId: string) => {
      await client.post(`/v2/todos/${todoId}:archive`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos"] });
    },
  });
};

/**
 * Hook to permanently delete a todo and all its associated data.
 *
 * @returns A mutation object for permanent deletion.
 */
export const useDeleteTodo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (todoId: string) => {
      await client.delete(`/v2/todos/${todoId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos"] });
    },
  });
};
