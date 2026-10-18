interface PaginationProps {
  currentPage: number;
  totalCount: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

/**
 * A simple numeric pagination component.
 * Automatically calculates total pages and renders clickable page numbers.
 *
 * @param currentPage - The current active page number.
 * @param totalCount - Total number of items across all pages.
 * @param pageSize - Number of items displayed per page.
 * @param onPageChange - Callback triggered when a new page is selected.
 */
export function Pagination({
  currentPage,
  totalCount,
  pageSize,
  onPageChange,
}: PaginationProps) {
  const totalPages = Math.ceil(totalCount / pageSize);

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-4 mt-8 pb-10">
      {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
        <button
          key={p}
          onClick={() => onPageChange(p)}
          className={`w-10 h-10 rounded-xl font-bold transition-all hover:scale-110 active:scale-95 cursor-pointer flex items-center justify-center ${
            p === currentPage
              ? "bg-brand-200/50 text-brand-400"
              : "text-gray-700 hover:bg-brand-200/50 hover:text-brand-400"
          }`}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
