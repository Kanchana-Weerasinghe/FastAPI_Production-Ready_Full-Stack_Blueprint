import { createFileRoute } from "@tanstack/react-router";

import { TodoEdit } from "../../../../features/todo/TodoEdit";

/**
 * Todo edit route.
 */
export const Route = createFileRoute("/_authenticated/todo/$todoId/edit")({
  component: TodoEdit,
});
