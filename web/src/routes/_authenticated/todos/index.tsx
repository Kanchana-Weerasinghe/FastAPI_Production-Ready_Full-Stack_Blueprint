import { createFileRoute } from "@tanstack/react-router";

import { TodoList } from "../../../features/todo/TodoList";

/**
 * Main todos dashboard route.
 */
export const Route = createFileRoute("/_authenticated/todos/")({
  component: TodoList,
});
