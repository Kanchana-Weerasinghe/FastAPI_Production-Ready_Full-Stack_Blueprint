import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "@/components/common/Pagination";

describe("Pagination", () => {
  it("renders nothing when there is only one page", () => {
    const { container } = render(
      <Pagination
        currentPage={1}
        totalCount={5}
        pageSize={10}
        onPageChange={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders the correct number of page buttons", () => {
    render(
      <Pagination
        currentPage={1}
        totalCount={30}
        pageSize={10}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.getAllByRole("button")).toHaveLength(3);
  });

  it("calls onPageChange with the correct page number when clicked", () => {
    const onPageChange = vi.fn();
    render(
      <Pagination
        currentPage={1}
        totalCount={30}
        pageSize={10}
        onPageChange={onPageChange}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "2" }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("renders nothing when totalCount is exactly one page", () => {
    const { container } = render(
      <Pagination
        currentPage={1}
        totalCount={10}
        pageSize={10}
        onPageChange={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("re-renders when props change", () => {
    const { rerender } = render(
      <Pagination
        currentPage={1}
        totalCount={30}
        pageSize={10}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.getAllByRole("button")).toHaveLength(3);

    rerender(
      <Pagination
        currentPage={1}
        totalCount={40}
        pageSize={10}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.getAllByRole("button")).toHaveLength(4);
  });
});
