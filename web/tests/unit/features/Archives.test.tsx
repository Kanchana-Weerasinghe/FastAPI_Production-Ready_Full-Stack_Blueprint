import { render, screen } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Archives } from "@/features/Archives";
import { useDeleteTodo, useToggleArchiveTodo } from "@/hooks/mutations/todos";

vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn() }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/hooks/shared/useDebounce", () => ({
  useDebounce: (v: string) => v,
}));
vi.mock("@/hooks/mutations/todos", () => ({
  useDeleteTodo: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useToggleArchiveTodo: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

const mockUseTodos = vi.fn();
vi.mock("@/hooks/queries/todos", () => ({
  useTodos: (...args: unknown[]) => mockUseTodos(...args),
}));

describe("Archives", () => {
  beforeEach(() => {
    mockUseTodos.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
    });
  });

  it("renders the search input", () => {
    render(<Archives />);
    expect(
      screen.getByPlaceholderText("Search archived todos..."),
    ).toBeInTheDocument();
  });

  it("shows the empty state when there is no data", () => {
    render(<Archives />);
    expect(screen.getByText("No archived todos found.")).toBeInTheDocument();
  });

  it("renders archive cards when todos are present", () => {
    mockUseTodos.mockReturnValue({
      data: {
        founds: [
          {
            id: "1",
            title: "Old Task",
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
    render(<Archives />);
    expect(screen.getByText("Old Task")).toBeInTheDocument();
  });

  it("updates search term when typing in search box", () => {
    render(<Archives />);
    const searchInput = screen.getByPlaceholderText("Search archived todos...");
    fireEvent.change(searchInput, { target: { value: "test" } });
    expect(searchInput).toHaveValue("test");
  });

  it("handles successful and failed restore", async () => {
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
            title: "Old Task",
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

    render(<Archives />);

    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText("Restore"));
    expect(mutateAsync).toHaveBeenCalledWith("1");

    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText("Restore"));
  });

  it("handles successful and failed delete", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));

    vi.mocked(useDeleteTodo).mockReturnValue({ mutateAsync } as never);
    mockUseTodos.mockReturnValue({
      data: {
        founds: [
          {
            id: "1",
            title: "Old Task",
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

    render(<Archives />);

    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText("Permanently delete"));
    fireEvent.click(screen.getByText("Delete Forever"));
    expect(mutateAsync).toHaveBeenCalledWith("1");

    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText("Permanently delete"));
    fireEvent.click(screen.getByText("Delete Forever"));
  });
});
