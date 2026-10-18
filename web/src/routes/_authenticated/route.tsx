import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";

import { Navbar } from "../../components/common/Navbar";
import { fetchUser } from "../../hooks/queries/user";
import { queryClient } from "../../lib/query";
import { authStore, setAuth } from "../../store/auth.store";

/**
 * Authenticated Layout Route.
 * - Enforces session verification via the 'auth-user' query before loading.
 * - Redirects unauthenticated users to the Landing page.
 * - Provides the shared Navbar and background theme for all private pages.
 */
export const Route = createFileRoute("/_authenticated")({
  beforeLoad: async ({ location }) => {
    if (!authStore.state.user) {
      try {
        const user = await queryClient.fetchQuery({
          queryKey: ["auth-user"],
          queryFn: fetchUser,
        });
        setAuth(user);
      } catch {
        throw redirect({
          to: "/",
        });
      }
    }
    if (location.pathname === "/") {
      throw redirect({ to: "/todos" });
    }
  },
  component: () => (
    <div className="min-h-screen bg-brand-100 flex flex-col">
      <Navbar />
      <Outlet />
    </div>
  ),
});
