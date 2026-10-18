import { createFileRoute } from "@tanstack/react-router";

import { Landing } from "../../features/Landing";

/**
 * Landing / Login page route.
 */
export const Route = createFileRoute("/_guest/")({
  component: Landing,
});
