import { createFileRoute } from "@tanstack/react-router";

import { Archives } from "../../features/Archives";

/**
 * Archive page route.
 */
export const Route = createFileRoute("/_authenticated/archives")({
  component: Archives,
});
