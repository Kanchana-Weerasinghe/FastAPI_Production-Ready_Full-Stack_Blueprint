import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Landing } from "@/features/Landing";
import { useSignIn, useSignUp } from "@/hooks/mutations/auth";

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/hooks/mutations/auth", () => ({
  useSignIn: vi.fn(() => ({
    mutateAsync: vi
      .fn()
      .mockResolvedValue({ mfaRequired: false, mfaToken: null }),
  })),
  useSignUp: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useMfaVerify: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}));

describe("Landing", () => {
  it("shows the Boost brand and links to the Boost Guide", () => {
    render(<Landing />);
    expect(screen.getByRole("heading", { name: "Boost" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Read the Boost Guide/ }),
    ).toHaveAttribute("href", "/guide/index.html");
  });

  it("renders email and password fields", () => {
    render(<Landing />);
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("••••••••")).toBeInTheDocument();
  });

  it("renders the Sign in submit button by default", () => {
    render(<Landing />);
    const buttons = screen.getAllByRole("button", { name: /sign in/i });
    expect(buttons).toHaveLength(2);
  });

  it("switches to Sign up mode when the Sign up tab is clicked and back to Sign in", () => {
    render(<Landing />);
    const signUpTab = screen.getByRole("button", { name: "Sign up" });
    fireEvent.click(signUpTab);
    expect(screen.getAllByRole("button", { name: /sign up/i })).toHaveLength(2);

    const signInTab = screen.getByRole("button", { name: "Sign in" });
    fireEvent.click(signInTab);
    expect(screen.getAllByRole("button", { name: /sign in/i })).toHaveLength(2);
  });

  it("handles input changes and blurs", () => {
    render(<Landing />);
    const emailInput = screen.getByPlaceholderText("you@example.com");
    const passwordInput = screen.getByPlaceholderText("••••••••");

    fireEvent.change(emailInput, { target: { value: "test@test.com" } });
    fireEvent.blur(emailInput);
    expect(emailInput).toHaveValue("test@test.com");

    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.blur(passwordInput);
    expect(passwordInput).toHaveValue("password123");
  });

  it("handles successful and failed sign in", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));
    vi.mocked(useSignIn).mockReturnValue({ mutateAsync } as never);

    render(<Landing />);
    const emailInput = screen.getByPlaceholderText("you@example.com");
    const passwordInput = screen.getByPlaceholderText("••••••••");
    fireEvent.change(emailInput, { target: { value: "test@test.com" } });
    fireEvent.blur(emailInput);
    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.blur(passwordInput);

    const form = emailInput.closest("form");
    fireEvent.submit(form!);
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    fireEvent.submit(form!);
  });

  it("handles successful and failed sign up", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));

    vi.mocked(useSignUp).mockReturnValue({ mutateAsync } as never);

    render(<Landing />);
    fireEvent.click(screen.getByRole("button", { name: "Sign up" }));

    const emailInput = screen.getByPlaceholderText("you@example.com");
    const passwordInput = screen.getByPlaceholderText("••••••••");
    fireEvent.change(emailInput, { target: { value: "test@test.com" } });
    fireEvent.blur(emailInput);
    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.blur(passwordInput);
    const form = emailInput.closest("form");
    fireEvent.submit(form!);
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    fireEvent.submit(form!);
  });
});
