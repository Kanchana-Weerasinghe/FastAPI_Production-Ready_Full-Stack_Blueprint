import { useState } from "react";
import { toast } from "sonner";

import { AssetCard } from "../components/AssetCard";
import { Pagination } from "../components/common/Pagination";
import { EmptyState } from "../components/Empty";
import { Search } from "../components/Search";
import { getAttachmentIcon } from "../constants/attachments.constants";
import { useRemoveAttachmentGeneric } from "../hooks/mutations/todos";
import { useAttachments } from "../hooks/queries/todos";
import { useDebounce } from "../hooks/shared/useDebounce";
import { formatDate, formatFileSize, getDownloadUrl } from "../utils/helper";

/**
 * The Global Attachments feature page.
 * Displays all uploaded files across all todos with filtering,
 * pagination, and management actions (Download/Delete).
 */
export function Attachments() {
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearch = useDebounce(searchTerm, 500);
  const { data, isLoading, isFetching } = useAttachments({
    fileName: debouncedSearch,
    page,
  });
  const { mutateAsync: removeAttachment } = useRemoveAttachmentGeneric();

  const handleDelete = async (fileId: string) => {
    try {
      await removeAttachment({ fileId });
      toast.success("Attachment deleted");
    } catch {
      toast.error("Failed to delete attachment");
    }
  };

  const attachments = data?.founds || [];
  const hasData = attachments.length > 0;

  return (
    <main className="flex-1 px-10 py-6 max-w-5xl w-full mx-auto animate-fade-in-up">
      <div className="mb-6 flex">
        <Search
          placeholder="Search files..."
          className="max-w-md"
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {isLoading || !hasData ? (
        <EmptyState isLoading={isLoading} message="No attachments found." />
      ) : (
        <div
          className={`transition-opacity duration-200 ${isFetching ? "opacity-50 pointer-events-none" : "opacity-100"}`}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {attachments.map((file) => (
              <AssetCard
                key={file.id}
                name={file.fileName}
                type={file.fileType}
                size={formatFileSize(file.fileSize)}
                date={formatDate(file.createdAt)}
                iconUrl={getAttachmentIcon(file.fileName)}
                onDownload={() =>
                  window.open(getDownloadUrl(file.id), "_blank")
                }
                onDelete={() => handleDelete(file.id)}
              />
            ))}
          </div>
        </div>
      )}

      {data && (
        <Pagination
          currentPage={page}
          totalCount={data.searchOptions.totalCount}
          pageSize={data.searchOptions.pageSize}
          onPageChange={setPage}
        />
      )}
    </main>
  );
}
