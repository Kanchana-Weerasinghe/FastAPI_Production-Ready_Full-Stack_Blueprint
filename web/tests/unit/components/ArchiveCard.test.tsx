import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ArchiveCard } from "@/components/ArchiveCard";

const todo = {
  id: "todo-1",
  title: "Old Project Notes",
  isCompleted: false,
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-03-01T00:00:00Z",
};

describe("ArchiveCard", () => {
  it("renders the todo title", () => {
    render(<ArchiveCard todo={todo} onRestore={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText("Old Project Notes")).toBeInTheDocument();
  });

  it("calls onRestore with the todo id when Restore is clicked", () => {
    const onRestore = vi.fn();
    render(
      <ArchiveCard todo={todo} onRestore={onRestore} onDelete={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText("Restore"));
    expect(onRestore).toHaveBeenCalledWith("todo-1");
  });

  it("opens the delete confirmation modal when 'Permanently delete' is clicked", () => {
    render(<ArchiveCard todo={todo} onRestore={vi.fn()} onDelete={vi.fn()} />);
    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText("Permanently delete"));
    expect(screen.getByText("Permanently Delete?")).toBeInTheDocument();
  });

  it("calls onDelete when the delete confirmation is accepted", () => {
    const onDelete = vi.fn();
    render(<ArchiveCard todo={todo} onRestore={vi.fn()} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText("Permanently delete"));
    fireEvent.click(screen.getByText("Delete Forever"));
    expect(onDelete).toHaveBeenCalledWith("todo-1");
  });

  it("closes the delete confirmation modal when 'Cancel' is clicked", () => {
    render(<ArchiveCard todo={todo} onRestore={vi.fn()} onDelete={vi.fn()} />);
    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText("Permanently delete"));
    expect(screen.getByText("Permanently Delete?")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByText("Permanently Delete?")).not.toBeInTheDocument();
  });
});
