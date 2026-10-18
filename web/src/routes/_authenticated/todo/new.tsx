import { createFileRoute } from "@tanstack/react-router";

import { TodoNew as NewTodo } from "../../../features/todo/TodoNew";

/**
 * New todo creation route.
 */
export const Route = createFileRoute("/_authenticated/todo/new")({
  component: NewTodo,
});
