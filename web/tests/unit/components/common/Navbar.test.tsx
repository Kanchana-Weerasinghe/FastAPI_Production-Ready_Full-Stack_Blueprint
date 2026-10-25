import { render as rtlRender, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { Navbar } from "@/components/common/Navbar";
import { NAV_ITEMS } from "@/constants/navbar.constants";
import { authStore, setAuth } from "@/store/auth.store";

import { createWrapper } from "../../../test_utils";

const navigateMock = vi.fn();

const render = (ui: ReactElement) =>
  rtlRender(ui, { wrapper: createWrapper() });

vi.mock("@tanstack/react-router", () => {
  let currentPath = "/home";
  return {
    useLocation: () => ({ pathname: currentPath }),
    useNavigate: () => navigateMock,
    __setCurrentPath: (path: string) => {
      currentPath = path;
    },
    Link: ({
      children,
      to,
      className,
    }: {
      children: React.ReactNode;
      to: string;
      className?: string;
    }) => {
      const isActive = currentPath.startsWith(to) && to !== "/";
      return (
        <a href={to} className={`${className} ${isActive ? "active" : ""}`}>
          {children}
        </a>
      );
    },
  };
});

describe("Navbar", () => {
  it("renders the brand logo link", () => {
    render(<Navbar />);
    expect(screen.getByText("Boost")).toBeInTheDocument();
  });

  it("renders all navigation items from NAV_ITEMS", () => {
    render(<Navbar />);
    NAV_ITEMS.forEach((item) => {
      expect(screen.getByText(item.label)).toBeInTheDocument();
    });
  });

  it("renders nav links with correct href attributes", () => {
    render(<Navbar />);
    NAV_ITEMS.forEach((item) => {
      const link = screen.getByText(item.label).closest("a");
      expect(link).toHaveAttribute("href", item.to);
    });
  });

  it("updates the animated indicator when an active link is present", () => {
    vi.useFakeTimers();
    render(<Navbar />);
    vi.advanceTimersByTime(50);
    vi.useRealTimers();
  });

  it("handles when no link is active", async () => {
    vi.useFakeTimers();
    const router = await import("@tanstack/react-router");
    (
      router as typeof router & { __setCurrentPath: (path: string) => void }
    ).__setCurrentPath("/unknown");
    render(<Navbar />);
    vi.advanceTimersByTime(50);
    vi.useRealTimers();
  });

  it("signs the user out and redirects to the landing page", async () => {
    setAuth({
      id: "user-1",
      email: "test@example.com",
      username: "testuser",
      role: "user",
      emailVerified: true,
      mfaEnabled: false,
    });
    render(<Navbar />);

    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith({ to: "/" });
    });
    expect(authStore.state.user).toBeNull();
  });
});
