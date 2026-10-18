import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TodoNew } from "@/features/todo/TodoNew";
import { useCreateTodo, useUploadAttachment } from "@/hooks/mutations/todos";

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/hooks/mutations/todos", () => ({
  useCreateTodo: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useUploadAttachment: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}));

describe("TodoNew", () => {
  it("renders the title and description input fields", () => {
    render(<TodoNew />);
    expect(screen.getByPlaceholderText("Title")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Tell your story..."),
    ).toBeInTheDocument();
  });

  it("handles form submission success and failure", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));
    vi.mocked(useCreateTodo).mockReturnValue({ mutateAsync } as never);

    render(<TodoNew />);
    const titleInput = screen.getByPlaceholderText("Title");
    const descInput = screen.getByPlaceholderText("Tell your story...");
    fireEvent.change(titleInput, { target: { value: "My New Todo" } });
    fireEvent.blur(titleInput);
    fireEvent.change(descInput, { target: { value: "My Description" } });
    fireEvent.blur(descInput);

    const form = titleInput.closest("form");
    fireEvent.submit(form!);
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    fireEvent.submit(form!);
  });

  it("handles file uploads, validation, and removal", async () => {
    const uploadMutateAsync = vi
      .fn()
      .mockResolvedValueOnce({
        id: "att-1",
        fileName: "test.png",
        fileType: "image/png",
        fileSize: 100,
      })
      .mockRejectedValueOnce(new Error("fail"));

    vi.mocked(useUploadAttachment).mockReturnValue({
      mutateAsync: uploadMutateAsync,
      isPending: false,
    } as never);

    render(<TodoNew />);

    const fileInput = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();
    const largeFile = new File(["a".repeat(60 * 1024 * 1024)], "large.png", {
      type: "image/png",
    });
    Object.defineProperty(largeFile, "size", { value: 60 * 1024 * 1024 });
    fireEvent.change(fileInput, { target: { files: [largeFile] } });
    const validFile = new File(["test"], "test.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [validFile] } });
    expect(await screen.findByText("test.png")).toBeInTheDocument();
    fireEvent.change(fileInput, { target: { files: [validFile] } });
    const removeBtn = screen.getByTitle("Delete");
    fireEvent.click(removeBtn);
    expect(screen.queryByText("test.png")).not.toBeInTheDocument();
  });
});
