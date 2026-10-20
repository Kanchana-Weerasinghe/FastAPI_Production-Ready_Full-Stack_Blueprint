import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TodoEdit } from "@/features/todo/TodoEdit";
import { useUpdateTodo } from "@/hooks/mutations/todos";

vi.mock("@tanstack/react-router", () => ({
  useNavigate: vi.fn(() => vi.fn()),
  useParams: () => ({ todoId: "1" }),
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/hooks/mutations/todos", () => ({
  useUpdateTodo: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

const mockUseTodo = vi.fn();
vi.mock("@/hooks/queries/todos", () => ({
  useTodo: (...args: unknown[]) => mockUseTodo(...args),
}));

describe("TodoEdit", () => {
  beforeEach(() => {
    mockUseTodo.mockReturnValue({ data: undefined, isLoading: true });
  });

  it("shows loading spinner initially", () => {
    const { container } = render(<TodoEdit />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("renders the edit form when data is available", () => {
    mockUseTodo.mockReturnValue({
      data: {
        id: "1",
        title: "Test Todo",
        description: "Test Description",
        isCompleted: false,
        createdAt: "2024-01-01T00:00:00Z",
        updatedAt: "2024-01-01T00:00:00Z",
      },
      isLoading: false,
    });
    render(<TodoEdit />);
    expect(screen.getByDisplayValue("Test Todo")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Test Description")).toBeInTheDocument();
  });

  it("handles form submission success and failure", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));
    vi.mocked(useUpdateTodo).mockReturnValue({ mutateAsync } as never);

    mockUseTodo.mockReturnValue({
      data: {
        id: "1",
        title: "Test Todo",
        description: "Test Description",
        isCompleted: false,
        createdAt: "",
        updatedAt: "",
      },
      isLoading: false,
    });
    render(<TodoEdit />);

    const titleInput = screen.getByDisplayValue("Test Todo");
    const descInput = screen.getByDisplayValue("Test Description");
    const form = titleInput.closest("form");

    fireEvent.change(titleInput, { target: { value: "Updated Title" } });
    fireEvent.blur(titleInput);
    fireEvent.change(descInput, { target: { value: "Updated Description" } });
    fireEvent.blur(descInput);

    fireEvent.submit(form!);
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    fireEvent.submit(form!);
  });

  it("renders the back link", () => {
    mockUseTodo.mockReturnValue({
      data: {
        id: "1",
        title: "Test Todo",
        description: "Test Description",
        isCompleted: false,
        createdAt: "",
        updatedAt: "",
      },
      isLoading: false,
    });

    render(<TodoEdit />);

    const backLink = screen.getByRole("link", { name: /back/i });
    expect(backLink).toBeInTheDocument();
  });
});
