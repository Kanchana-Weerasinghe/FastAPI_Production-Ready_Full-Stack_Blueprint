import { render, screen } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Attachments } from "@/features/Attachments";
import { useRemoveAttachmentGeneric } from "@/hooks/mutations/todos";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/hooks/shared/useDebounce", () => ({
  useDebounce: (v: string) => v,
}));
vi.mock("@/hooks/mutations/todos", () => ({
  useRemoveAttachmentGeneric: vi.fn(() => ({ mutateAsync: vi.fn() })),
}));

const mockUseAttachments = vi.fn();
vi.mock("@/hooks/queries/todos", () => ({
  useAttachments: (...args: unknown[]) => mockUseAttachments(...args),
}));

describe("Attachments", () => {
  beforeEach(() => {
    mockUseAttachments.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
    });
  });

  it("renders the search input", () => {
    render(<Attachments />);
    expect(screen.getByPlaceholderText("Search files...")).toBeInTheDocument();
  });

  it("shows the empty state when there are no attachments", () => {
    render(<Attachments />);
    expect(screen.getByText("No attachments found.")).toBeInTheDocument();
  });

  it("renders attachment cards when files are present", () => {
    mockUseAttachments.mockReturnValue({
      data: {
        founds: [
          {
            id: "att-1",
            fileName: "report.pdf",
            fileType: "application/pdf",
            fileSize: 1024,
            createdAt: "2024-01-01T00:00:00Z",
            updatedAt: "2024-01-01T00:00:00Z",
          },
        ],
        searchOptions: { totalCount: 1, pageSize: 10, currentPage: 1 },
      },
      isLoading: false,
      isFetching: false,
    });
    render(<Attachments />);
    expect(screen.getByText("report.pdf")).toBeInTheDocument();
  });

  it("updates search term when typing in search box", () => {
    render(<Attachments />);
    const searchInput = screen.getByPlaceholderText("Search files...");
    fireEvent.change(searchInput, { target: { value: "test" } });
    expect(searchInput).toHaveValue("test");
  });

  it("handles successful and failed delete", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error("fail"));

    vi.mocked(useRemoveAttachmentGeneric).mockReturnValue({
      mutateAsync,
    } as never);
    mockUseAttachments.mockReturnValue({
      data: {
        founds: [
          {
            id: "att-1",
            fileName: "doc.txt",
            fileType: "text/plain",
            fileSize: 10,
            createdAt: "",
            updatedAt: "",
          },
        ],
        searchOptions: { totalCount: 1, pageSize: 10, currentPage: 1 },
      },
    });

    render(<Attachments />);

    fireEvent.click(screen.getByTitle("Delete"));
    expect(mutateAsync).toHaveBeenCalledWith({ fileId: "att-1" });

    fireEvent.click(screen.getByTitle("Delete"));
  });

  it("opens download url when download button is clicked", () => {
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    mockUseAttachments.mockReturnValue({
      data: {
        founds: [
          {
            id: "att-1",
            fileName: "doc.txt",
            fileType: "text/plain",
            fileSize: 10,
            createdAt: "",
            updatedAt: "",
          },
        ],
        searchOptions: { totalCount: 1, pageSize: 10, currentPage: 1 },
      },
    });

    render(<Attachments />);
    fireEvent.click(screen.getByTitle("Download"));
    expect(openSpy).toHaveBeenCalled();
    openSpy.mockRestore();
  });
});
