import { createRootRoute, Outlet } from "@tanstack/react-router";
import * as React from "react";
import { Toaster } from "sonner";

/**
 * The Root Route of the application.
 * Provides the global layout context and initializes global UI components
 * like the Sonner Toaster for notifications.
 */
export const Route = createRootRoute({
  component: () => (
    <React.Fragment>
      <Outlet />
      <Toaster
        position="top-center"
        closeButton
        duration={1000}
        toastOptions={{
          classNames: {
            toast:
              "!font-mono !text-sm !border-2 !bg-white !rounded-xl !shadow-xl !text-brand-600",
            title: "!text-base !font-bold",
            description: "!text-sm !font-bold !text-brand-300/60",
            success: "!border-brand-400 !text-brand-400",
            error: "!border-red-400 !text-red-500",
          },
          style: {
            fontFamily: "var(--font-mono)",
          },
        }}
      />
    </React.Fragment>
  ),
});
