import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Input } from "@/components/common/Input";

describe("Input", () => {
  it("renders an input element", () => {
    render(<Input />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("renders a label when the label prop is provided", () => {
    render(<Input id="email" label="Email Address" />);
    expect(screen.getByText("Email Address")).toBeInTheDocument();
  });

  it("displays an error message when the error prop is set", () => {
    render(<Input error="This field is required" />);
    expect(screen.getByText("This field is required")).toBeInTheDocument();
  });

  it("sets aria-invalid when an error is present", () => {
    render(<Input error="Invalid input" />);
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "true");
  });

  it("does not set aria-invalid when there is no error", () => {
    render(<Input />);
    expect(screen.getByRole("textbox")).toHaveAttribute(
      "aria-invalid",
      "false",
    );
  });

  it("applies the ghost variant styles", () => {
    render(<Input variant="ghost" className="my-class" />);
    const input = screen.getByRole("textbox");
    expect(input.className).toContain("bg-transparent");
    expect(input.className).toContain("my-class");
  });

  it("re-renders when props change", () => {
    const { rerender } = render(<Input value="first" readOnly />);
    rerender(<Input value="second" readOnly />);
    expect(screen.getByRole("textbox")).toHaveValue("second");
  });
});
