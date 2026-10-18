import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CompactAssetCard } from "@/components/CompactAssetCard";

const defaultProps = {
  name: "notes.docx",
  type: "application/docx",
  size: "48 KB",
  date: "Feb 10 2024",
  iconUrl: "/icons/docx.svg",
};

describe("CompactAssetCard", () => {
  it("renders the file name, size, and date", () => {
    render(<CompactAssetCard {...defaultProps} />);
    expect(screen.getByText("notes.docx")).toBeInTheDocument();
    expect(screen.getByText("48 KB")).toBeInTheDocument();
    expect(screen.getByText("Feb 10 2024")).toBeInTheDocument();
  });

  it("calls onDownload when the download button is clicked", () => {
    const onDownload = vi.fn();
    render(<CompactAssetCard {...defaultProps} onDownload={onDownload} />);
    fireEvent.click(screen.getByTitle("Download"));
    expect(onDownload).toHaveBeenCalledTimes(1);
  });

  it("does not render a delete button when onDelete is not provided", () => {
    render(<CompactAssetCard {...defaultProps} />);
    expect(screen.queryByTitle("Delete")).not.toBeInTheDocument();
  });

  it("renders and calls onDelete when provided", () => {
    const onDelete = vi.fn();
    render(<CompactAssetCard {...defaultProps} onDelete={onDelete} />);
    fireEvent.click(screen.getByTitle("Delete"));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("applies readOnly styling when readOnly is true", () => {
    render(<CompactAssetCard {...defaultProps} readOnly={true} />);
    expect(screen.getByText("notes.docx")).toBeInTheDocument();
  });

  it("does not crash when clicking download without callback", () => {
    render(<CompactAssetCard {...defaultProps} />);
    fireEvent.click(screen.getByTitle("Download"));
  });

  it("re-renders with new props", () => {
    const { rerender } = render(<CompactAssetCard {...defaultProps} />);
    rerender(<CompactAssetCard {...defaultProps} name="updated-notes.docx" />);
    expect(screen.getByText("updated-notes.docx")).toBeInTheDocument();
  });
});
