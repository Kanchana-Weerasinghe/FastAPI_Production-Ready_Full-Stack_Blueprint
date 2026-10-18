import { createFileRoute } from "@tanstack/react-router";

import { Attachments } from "../../features/Attachments";

/**
 * Global attachments page route.
 */
export const Route = createFileRoute("/_authenticated/attachments")({
  component: Attachments,
});
