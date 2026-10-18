import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TodoEdit } from "@/features/todo/TodoEdit";
import { useUpdateTodo, useUploadAttachment } from "@/hooks/mutations/todos";

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
  useRemoveAttachment: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useUploadAttachment: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
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
        attachments: [],
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
        attachments: [],
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

  it("handles file uploads, size validation, and deleting pending attachments", async () => {
    const uploadMutateAsync = vi
      .fn()
      .mockResolvedValueOnce({
        id: "att-2",
        fileName: "new.png",
        fileType: "image/png",
        fileSize: 100,
      })
      .mockRejectedValueOnce(new Error("fail"));

    vi.mocked(useUploadAttachment).mockReturnValue({
      mutateAsync: uploadMutateAsync,
      isPending: false,
    } as never);
    mockUseTodo.mockReturnValue({
      data: {
        id: "1",
        title: "Test Todo",
        description: "Test Description",
        isCompleted: false,
        createdAt: "",
        updatedAt: "",
        attachments: [],
      },
      isLoading: false,
    });

    render(<TodoEdit />);
    const fileInput = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const largeFile = new File(["a".repeat(60 * 1024 * 1024)], "large.png", {
      type: "image/png",
    });
    Object.defineProperty(largeFile, "size", { value: 60 * 1024 * 1024 });
    fireEvent.change(fileInput, { target: { files: [largeFile] } });
    const validFile = new File(["test"], "test.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [validFile] } });
    expect(await screen.findByText("new.png")).toBeInTheDocument();
    fireEvent.change(fileInput, { target: { files: [validFile] } });
    fireEvent.click(screen.getByTitle("Delete"));
    expect(screen.queryByText("new.png")).not.toBeInTheDocument();
  });

  it("handles deleting existing attachments", async () => {
    mockUseTodo.mockReturnValue({
      data: {
        id: "1",
        title: "Test Todo",
        description: "",
        isCompleted: false,
        createdAt: "",
        updatedAt: "",
        attachments: [
          {
            id: "att-1",
            fileName: "old.png",
            fileType: "image/png",
            fileSize: 100,
          },
        ],
      },
      isLoading: false,
    });
    render(<TodoEdit />);

    const removeBtn = screen.getByTitle("Delete");
    fireEvent.click(removeBtn);
    await waitFor(() =>
      expect(screen.queryByText("old.png")).not.toBeInTheDocument(),
    );
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
        attachments: [],
      },
      isLoading: false,
    });

    render(<TodoEdit />);

    const backLink = screen.getByRole("link", { name: /back/i });
    expect(backLink).toBeInTheDocument();
  });
});
