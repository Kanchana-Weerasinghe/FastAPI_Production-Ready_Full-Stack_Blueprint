import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TodoNew } from "@/features/todo/TodoNew";
import { useCreateTodo } from "@/hooks/mutations/todos";

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/hooks/mutations/todos", () => ({
  useCreateTodo: vi.fn(() => ({ mutateAsync: vi.fn() })),
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
});
