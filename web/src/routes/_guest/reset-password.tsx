import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { ResetPassword } from "../../features/auth/ResetPassword";

export const Route = createFileRoute("/_guest/reset-password")({
  validateSearch: z.object({ token: z.string().optional() }),
  component: function ResetPasswordRoute() {
    const { token } = Route.useSearch();
    return <ResetPassword token={token} />;
  },
});
