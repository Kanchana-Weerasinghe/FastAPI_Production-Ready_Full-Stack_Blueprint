import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState } from "@/components/Empty";

describe("EmptyState", () => {
  it("renders default message when no props are provided", () => {
    render(<EmptyState />);
    expect(screen.getByText("No items found.")).toBeInTheDocument();
  });

  it("renders a custom message when provided", () => {
    render(<EmptyState message="Nothing here yet" />);
    expect(screen.getByText("Nothing here yet")).toBeInTheDocument();
  });

  it("renders a sub-message when provided", () => {
    render(
      <EmptyState message="Empty" subMessage="Try adding something new" />,
    );
    expect(screen.getByText("Try adding something new")).toBeInTheDocument();
  });

  it("renders a spinner when isLoading is true", () => {
    const { container } = render(<EmptyState isLoading />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("does not render the empty message when isLoading is true", () => {
    render(<EmptyState isLoading message="No items found." />);
    expect(screen.queryByText("No items found.")).not.toBeInTheDocument();
  });
});
