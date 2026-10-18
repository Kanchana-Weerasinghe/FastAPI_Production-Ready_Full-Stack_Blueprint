import { createFileRoute } from "@tanstack/react-router";

import { ForgotPassword } from "../../features/auth/ForgotPassword";

export const Route = createFileRoute("/_guest/forgot-password")({
  component: ForgotPassword,
});
