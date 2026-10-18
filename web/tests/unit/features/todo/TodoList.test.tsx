import { render, screen } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TodoList } from "@/features/todo/TodoList";
import {
  useToggleArchiveTodo,
  useUpdateTodoGeneric,
} from "@/hooks/mutations/todos";

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/hooks/shared/useDebounce", () => ({
  useDebounce: (v: string) => v,
}));
vi.mock("@/hooks/mutations/todos", () => ({
  useToggleArchiveTodo: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useUpdateTodoGeneric: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

const mockUseTodos = vi.fn();
vi.mock("@/hooks/queries/todos", () => ({
  useTodos: (...args: unknown[]) => mockUseTodos(...args),
}));

describe("TodoList", () => {
  beforeEach(() => {
    mockUseTodos.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
    });
  });

  it("renders the search input", () => {
    render(<TodoList />);
    expect(screen.getByPlaceholderText("Search todos...")).toBeInTheDocument();
  });

  it("renders the Add Todo button linking to /todo/new", () => {
    render(<TodoList />);
    const link = screen.getByRole("link", { name: /add todo/i });
    expect(link).toHaveAttribute("href", "/todo/new");
  });

  it("shows the empty state when there are no todos", () => {
    render(<TodoList />);
    expect(screen.getByText("No todos found.")).toBeInTheDocument();
  });

  it("renders todo cards when data is available", () => {
    mockUseTodos.mockReturnValue({
      data: {
        founds: [
          {
            id: "1",
            title: "Fix the bug",
            isCompleted: false,
            createdAt: "2024-01-01T00:00:00Z",
            updatedAt: "2024-01-01T00:00:00Z",
          },
        ],
        searchOptions: { totalCount: 1, pageSize: 10, currentPage: 1 },
      },
      isLoading: false,
      isFetching: false,
    });
    render(<TodoList />);
    expect(screen.getByText("Fix the bug")).toBeInTheDocument();
  });

  it("updates search term when typing in search box", () => {
    render(<TodoList />);
    const searchInput = screen.getByPlaceholderText("Search todos...");
    fireEvent.change(searchInput, { target: { value: "test" } });
    expect(searchInput).toHaveValue("test");
  });

  it("handles successful and failed archive", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));

    vi.mocked(useToggleArchiveTodo).mockReturnValue({ mutateAsync } as never);
    mockUseTodos.mockReturnValue({
      data: {
        founds: [
          {
            id: "1",
            title: "Task",
            isCompleted: false,
            createdAt: "",
            updatedAt: "",
          },
        ],
        searchOptions: { totalCount: 1, pageSize: 10, currentPage: 1 },
      },
      isLoading: false,
      isFetching: false,
    });

    render(<TodoList />);

    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Delete"));
    const deleteButtons1 = screen.getAllByText("Delete");
    fireEvent.click(deleteButtons1[deleteButtons1.length - 1]);
    expect(mutateAsync).toHaveBeenCalledWith("1");
    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Delete"));
    const deleteButtons2 = screen.getAllByText("Delete");
    fireEvent.click(deleteButtons2[deleteButtons2.length - 1]);
  });

  it("handles successful and failed toggle status", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));

    vi.mocked(useUpdateTodoGeneric).mockReturnValue({ mutateAsync } as never);
    mockUseTodos.mockReturnValue({
      data: {
        founds: [
          {
            id: "1",
            title: "Task",
            isCompleted: false,
            createdAt: "",
            updatedAt: "",
          },
        ],
        searchOptions: { totalCount: 1, pageSize: 10, currentPage: 1 },
      },
      isLoading: false,
      isFetching: false,
    });

    const { rerender } = render(<TodoList />);

    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Mark as completed"));
    expect(mutateAsync).toHaveBeenCalledWith({
      todoId: "1",
      data: { isCompleted: true },
    });

    mockUseTodos.mockReturnValue({
      data: {
        founds: [
          {
            id: "1",
            title: "Task",
            isCompleted: true,
            createdAt: "",
            updatedAt: "",
          },
        ],
        searchOptions: { totalCount: 1, pageSize: 10, currentPage: 1 },
      },
      isLoading: false,
      isFetching: false,
    });
    rerender(<TodoList />);

    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Mark as incomplete"));

    fireEvent.click(screen.getByRole("button", { name: "Options" }));
    fireEvent.click(screen.getByText("Mark as incomplete"));
  });
});
