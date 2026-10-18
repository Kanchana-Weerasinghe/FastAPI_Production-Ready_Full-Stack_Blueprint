import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { VerifyEmail } from "../features/auth/VerifyEmail";

/** Public: works whether or not the user is signed in on this device. */
export const Route = createFileRoute("/verify-email")({
  validateSearch: z.object({ token: z.string().optional() }),
  component: function VerifyEmailRoute() {
    const { token } = Route.useSearch();
    return <VerifyEmail token={token} />;
  },
});
