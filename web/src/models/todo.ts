import { z } from "zod";

/**
 * Zod schema for creating a new todo.
 * Used for form validation in both 'New' and 'Edit' features.
 */
export const todoSchema = z.object({
  title: z
    .string()
    .min(1, "Title is missing")
    .max(100, "Must be less than 100 characters"),
  description: z.string().optional(),
  attachmentIds: z.array(z.string()).optional(),
});

export type TodoFormValues = z.infer<typeof todoSchema>;

export const todoUpdateSchema = todoSchema.extend({
  isCompleted: z.boolean().optional(),
});

export type TodoUpdate = z.infer<typeof todoUpdateSchema>;

import { attachmentSchema } from "./attachment";

/**
 * Zod schema for a full Todo object returned by the API.
 * Includes nested attachment details.
 */
export const todoResponseSchema = z.object({
  id: z.string(),
  userId: z.string(),
  title: z.string(),
  description: z.string().optional(),
  isCompleted: z.boolean(),
  attachments: z.array(attachmentSchema).default([]),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export type Todo = z.infer<typeof todoResponseSchema>;

export const todoListItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  isCompleted: z.boolean(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export type TodoListItem = z.infer<typeof todoListItemSchema>;

export const todoListResponseSchema = z.object({
  founds: z.array(todoListItemSchema),
  searchOptions: z.record(z.string(), z.any()),
});

export type TodoListResponse = z.infer<typeof todoListResponseSchema>;

/**
 * Zod schema for Todo search and filter parameters.
 * Validates query parameters for the /v2/todos/ endpoint.
 */
export const findTodoParamsSchema = z.object({
  title: z.string().optional(),
  userId: z.string().optional(),
  page: z.number().optional(),
  pageSize: z.number().optional(),
  ordering: z.string().optional(),
  isActive: z.boolean().optional(),
});

export type FindTodoParams = z.infer<typeof findTodoParamsSchema>;
