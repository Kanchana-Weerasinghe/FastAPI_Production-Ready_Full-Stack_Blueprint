import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";

import { fetchUser } from "../../hooks/queries/user";
import { queryClient } from "../../lib/query";
import { authStore, setAuth } from "../../store/auth.store";

/**
 * Guest Layout Route.
 * - Prevents authenticated users from accessing public/landing pages.
 * - Automatically redirects logged-in users to the '/home' page.
 */
export const Route = createFileRoute("/_guest")({
  beforeLoad: async () => {
    if (!authStore.state.user) {
      try {
        const user = await queryClient.fetchQuery({
          queryKey: ["auth-user"],
          queryFn: fetchUser,
        });
        setAuth(user);
      } catch {
        console.error("Authentication failed");
      }
    }
    if (authStore.state.user) {
      throw redirect({
        to: "/home",
      });
    }
  },
  component: () => <Outlet />,
});
