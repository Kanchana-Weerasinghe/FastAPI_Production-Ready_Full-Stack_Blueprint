import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Search } from "@/components/Search";

describe("Search", () => {
  it("renders with the default placeholder", () => {
    render(<Search />);
    expect(screen.getByPlaceholderText("Search...")).toBeInTheDocument();
  });

  it("renders with a custom placeholder", () => {
    render(<Search placeholder="Find a todo..." />);
    expect(screen.getByPlaceholderText("Find a todo...")).toBeInTheDocument();
  });

  it("calls onChange when the user types", () => {
    const onChange = vi.fn();
    render(<Search onChange={onChange} />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "groceries" },
    });
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("re-renders when props change", () => {
    const { rerender } = render(<Search placeholder="Original" />);
    rerender(<Search placeholder="Updated" className="custom-class" />);
    expect(screen.getByPlaceholderText("Updated")).toBeInTheDocument();
  });
});
