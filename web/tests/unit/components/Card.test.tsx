import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Card } from "@/components/Card";

const defaultProps = {
  title: "Buy groceries",
  metadataLabel: "Created",
  metadataValue: "May 10 2024",
};

describe("Card", () => {
  it("renders the title and metadata", () => {
    render(<Card {...defaultProps} />);
    expect(screen.getByText("Buy groceries")).toBeInTheDocument();
    expect(screen.getByText("Created:")).toBeInTheDocument();
    expect(screen.getByText("May 10 2024")).toBeInTheDocument();
  });

  it("calls onClick when the card is clicked", () => {
    const onClick = vi.fn();
    render(<Card {...defaultProps} onClick={onClick} />);
    fireEvent.click(screen.getByText("Buy groceries"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("opens the dropdown menu when the menu button is clicked", () => {
    const menuOptions = [{ label: "Edit", onClick: vi.fn() }];
    render(<Card {...defaultProps} menuOptions={menuOptions} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Edit")).toBeInTheDocument();
  });

  it("calls the menu option handler when a menu item is clicked", () => {
    const onEdit = vi.fn();
    const menuOptions = [{ label: "Edit", onClick: onEdit }];
    render(<Card {...defaultProps} menuOptions={menuOptions} />);
    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Edit"));
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it("closes the dropdown menu when clicking outside", () => {
    const menuOptions = [{ label: "Edit", onClick: vi.fn() }];
    render(<Card {...defaultProps} menuOptions={menuOptions} />);
    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    expect(screen.getByText("Edit")).toBeInTheDocument();
    fireEvent.mouseDown(document.body);
    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
  });

  it("does not close the dropdown when clicking inside the menu", () => {
    const menuOptions = [{ label: "Edit", onClick: vi.fn() }];
    render(<Card {...defaultProps} menuOptions={menuOptions} />);
    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.mouseDown(screen.getByText("Edit").parentElement!);
    expect(screen.getByText("Edit")).toBeInTheDocument();
  });

  it("renders custom actions instead of menuOptions", () => {
    render(<Card {...defaultProps} actions={<button>Custom Action</button>} />);
    expect(screen.getByText("Custom Action")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Options" }),
    ).not.toBeInTheDocument();
  });

  it("renders an icon when provided", () => {
    render(
      <Card
        {...defaultProps}
        icon={<span data-testid="test-icon">Icon</span>}
      />,
    );
    expect(screen.getByTestId("test-icon")).toBeInTheDocument();
  });
});
