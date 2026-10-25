import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GUIDE_URL } from "@/constants/guide.constants";
import { Home } from "@/features/Home";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("@/hooks/queries/user", () => ({
  useUser: () => ({ data: { email: "ada@example.com" } }),
}));

describe("Home", () => {
  it("greets the signed-in user", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { name: "Welcome to Boost" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Signed in as ada@example.com"),
    ).toBeInTheDocument();
  });

  it("links to the Boost Guide, its quick start and the account page", () => {
    render(<Home />);
    expect(
      screen.getByRole("link", { name: "Open the guide" }),
    ).toHaveAttribute("href", GUIDE_URL);
    expect(screen.getByRole("link", { name: /Quick start/ })).toHaveAttribute(
      "href",
      `${GUIDE_URL}#quick-start`,
    );
    expect(
      screen.getByRole("link", { name: "Account security" }),
    ).toHaveAttribute("href", "/account");
  });
});
