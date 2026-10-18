import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssetCard } from "@/components/AssetCard";

const defaultProps = {
  name: "report.pdf",
  type: "application/pdf",
  size: "200 KB",
  date: "Jan 1 2024",
  iconUrl: "/icons/pdf.svg",
};

describe("AssetCard", () => {
  it("renders the file name", () => {
    render(<AssetCard {...defaultProps} />);
    expect(screen.getByText("report.pdf")).toBeInTheDocument();
  });

  it("renders the file size and date", () => {
    render(<AssetCard {...defaultProps} />);
    expect(screen.getByText("200 KB")).toBeInTheDocument();
    expect(screen.getByText("Jan 1 2024")).toBeInTheDocument();
  });

  it("calls onDownload when the download button is clicked", () => {
    const onDownload = vi.fn();
    render(<AssetCard {...defaultProps} onDownload={onDownload} />);
    fireEvent.click(screen.getByTitle("Download"));
    expect(onDownload).toHaveBeenCalledTimes(1);
  });

  it("calls onDelete when the delete button is clicked", () => {
    const onDelete = vi.fn();
    render(<AssetCard {...defaultProps} onDelete={onDelete} />);
    fireEvent.click(screen.getByTitle("Delete"));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("does not crash when clicking download/delete without callbacks", () => {
    render(<AssetCard {...defaultProps} />);
    fireEvent.click(screen.getByTitle("Download"));
    fireEvent.click(screen.getByTitle("Delete"));
  });

  it("re-renders with new props", () => {
    const { rerender } = render(<AssetCard {...defaultProps} />);
    rerender(<AssetCard {...defaultProps} name="updated-report.pdf" />);
    expect(screen.getByText("updated-report.pdf")).toBeInTheDocument();
  });
});
