import { createFileRoute } from "@tanstack/react-router";

import { TodoDetail } from "../../../../features/todo/TodoDetail";

/**
 * Todo detail route.
 */
export const Route = createFileRoute("/_authenticated/todo/$todoId/")({
  component: TodoDetail,
});
