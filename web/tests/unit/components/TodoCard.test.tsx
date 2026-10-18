import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TodoCard } from "@/components/TodoCard";

const mockNavigate = vi.fn();
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => mockNavigate,
}));

const todo = {
  id: "todo-1",
  title: "Fix the login bug",
  isCompleted: false,
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-02T00:00:00Z",
};

describe("TodoCard", () => {
  it("renders the todo title", () => {
    render(<TodoCard todo={todo} />);
    expect(screen.getByText("Fix the login bug")).toBeInTheDocument();
  });

  it("calls onToggle with the todo id when 'Mark as completed' is clicked", () => {
    const onToggle = vi.fn();
    render(<TodoCard todo={todo} onToggle={onToggle} />);
    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Mark as completed"));
    expect(onToggle).toHaveBeenCalledWith("todo-1");
  });

  it("opens the delete modal when 'Delete' menu option is clicked", () => {
    render(<TodoCard todo={todo} onDelete={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Delete"));
    expect(screen.getByText("Delete Todo?")).toBeInTheDocument();
  });

  it("calls onDelete when delete is confirmed and closes modal on cancel", () => {
    const onDelete = vi.fn();
    render(<TodoCard todo={todo} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Delete"));

    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByText("Delete Todo?")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Delete"));

    const deleteButtons = screen.getAllByText("Delete");
    fireEvent.click(deleteButtons[deleteButtons.length - 1]);
    expect(onDelete).toHaveBeenCalledWith("todo-1");
  });

  it("navigates to details page when the card is clicked", () => {
    mockNavigate.mockClear();
    render(<TodoCard todo={todo} />);
    fireEvent.click(screen.getByText("Fix the login bug"));
    expect(mockNavigate).toHaveBeenCalledWith({
      to: "/todo/$todoId",
      params: { todoId: "todo-1" },
    });
  });

  it("navigates to edit page when 'Edit' is clicked", () => {
    mockNavigate.mockClear();
    render(<TodoCard todo={todo} />);
    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Edit"));
    expect(mockNavigate).toHaveBeenCalledWith({
      to: "/todo/$todoId/edit",
      params: { todoId: "todo-1" },
    });
  });

  it("re-renders when props change", () => {
    const { rerender } = render(<TodoCard todo={todo} />);
    rerender(<TodoCard todo={{ ...todo, title: "Updated bug" }} />);
    expect(screen.getByText("Updated bug")).toBeInTheDocument();
  });
});
