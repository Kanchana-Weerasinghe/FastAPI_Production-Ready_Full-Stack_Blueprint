import { useMutation, useQueryClient } from "@tanstack/react-query";

import client from "../../lib/client";
import type { Attachment } from "../../models/attachment";
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

/**
 * Hook to upload a file as an attachment.
 *
 * @param todoId - Optional todo ID to invalidate detail queries after upload.
 * @returns A mutation object that returns the uploaded Attachment data.
 */
export const useUploadAttachment = (todoId?: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);

      const response = await client.post<Attachment>(
        "/v2/attachments/",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        },
      );
      return response.data;
    },
    onSuccess: () => {
      if (todoId) {
        queryClient.invalidateQueries({ queryKey: ["todos", todoId] });
      }
      queryClient.invalidateQueries({ queryKey: ["attachments"] });
    },
  });
};

/**
 * Hook to remove a specific attachment from a todo.
 *
 * @param todoId - The ID of the todo owning the attachment.
 * @returns A mutation object for removing a specific attachment.
 */
export const useRemoveAttachment = (todoId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (fileId: string) => {
      await client.delete(`/v2/attachments/${fileId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos", todoId] });
      queryClient.invalidateQueries({ queryKey: ["attachments"] });
    },
  });
};

/**
 * A generic hook to delete an attachment by its file ID globally.
 *
 * @returns A mutation object for global attachment deletion.
 */
export const useRemoveAttachmentGeneric = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ fileId }: { fileId: string }) => {
      await client.delete(`/v2/attachments/${fileId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attachments"] });
      queryClient.invalidateQueries({ queryKey: ["todos"] });
    },
  });
};
