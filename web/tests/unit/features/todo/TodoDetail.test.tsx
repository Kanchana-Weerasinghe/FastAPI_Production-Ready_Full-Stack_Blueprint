import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TodoDetail } from "@/features/todo/TodoDetail";
import { useToggleArchiveTodo, useUpdateTodo } from "@/hooks/mutations/todos";

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({ todoId: "1" }),
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/hooks/mutations/todos", () => ({
  useToggleArchiveTodo: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useUpdateTodo: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

const mockUseTodo = vi.fn();
vi.mock("@/hooks/queries/todos", () => ({
  useTodo: (...args: unknown[]) => mockUseTodo(...args),
}));

describe("TodoDetail", () => {
  beforeEach(() => {
    mockUseTodo.mockReturnValue({ data: undefined, isLoading: true });
  });

  it("shows loading spinner initially", () => {
    const { container } = render(<TodoDetail />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("shows not found message if todo does not exist", () => {
    mockUseTodo.mockReturnValue({ data: null, isLoading: false });
    render(<TodoDetail />);
    expect(screen.getByText("Todo not found.")).toBeInTheDocument();
  });

  it("renders todo details when data is available", () => {
    mockUseTodo.mockReturnValue({
      data: {
        id: "1",
        title: "Test Todo",
        description: "",
        isCompleted: true,
        createdAt: "2024-01-01T00:00:00Z",
        updatedAt: "2024-01-01T00:00:00Z",
      },
      isLoading: false,
    });
    render(<TodoDetail />);
    expect(screen.getByDisplayValue("Test Todo")).toBeInTheDocument();
    expect(screen.getByText("Tell your story...")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("handles successful and failed delete", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));

    vi.mocked(useToggleArchiveTodo).mockReturnValue({ mutateAsync } as never);
    mockUseTodo.mockReturnValue({
      data: {
        id: "1",
        title: "Test",
        isCompleted: false,
        createdAt: "",
        updatedAt: "",
      },
      isLoading: false,
    });

    render(<TodoDetail />);

    fireEvent.click(screen.getByRole("button", { name: /delete/i }));
    const deleteBtns1 = screen.getAllByRole("button", { name: "Delete" });
    fireEvent.click(deleteBtns1[deleteBtns1.length - 1]);
    expect(mutateAsync).toHaveBeenCalledWith("1");

    fireEvent.click(screen.getByRole("button", { name: /delete/i }));
    const deleteBtns2 = screen.getAllByRole("button", { name: "Delete" });
    fireEvent.click(deleteBtns2[deleteBtns2.length - 1]);
  });

  it("handles successful and failed toggle status", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));

    vi.mocked(useUpdateTodo).mockReturnValue({ mutateAsync } as never);
    mockUseTodo.mockReturnValue({
      data: {
        id: "1",
        title: "Test",
        isCompleted: false,
        createdAt: "",
        updatedAt: "",
      },
      isLoading: false,
    });

    render(<TodoDetail />);

    fireEvent.click(screen.getByRole("button", { name: /mark as completed/i }));
    expect(mutateAsync).toHaveBeenCalledWith({ isCompleted: true });
    fireEvent.click(screen.getByRole("button", { name: /mark as completed/i }));
  });
});
