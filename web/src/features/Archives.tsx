import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";

import { ArchiveCard } from "../components/ArchiveCard";
import { Pagination } from "../components/common/Pagination";
import { EmptyState } from "../components/Empty";
import { Search } from "../components/Search";
import { useDeleteTodo, useToggleArchiveTodo } from "../hooks/mutations/todos";
import { useTodos } from "../hooks/queries/todos";
import { useDebounce } from "../hooks/shared/useDebounce";

/**
 * The Archives feature page.
 * Manages the list of inactive/archived todos with search, pagination,
 * and the ability to restore or permanently delete items.
 */
export function Archives() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearch = useDebounce(searchTerm, 500);
  const { data, isLoading, isFetching } = useTodos({
    isActive: false,
    title: debouncedSearch,
    page,
  });
  const { mutateAsync: toggleArchive } = useToggleArchiveTodo();
  const { mutateAsync: deleteTodo } = useDeleteTodo();

  const handleRestore = async (id: string) => {
    try {
      await toggleArchive(id);
      toast.success("Todo restored", {
        description: "The todo has been moved back to your active list.",
      });
      navigate({ to: "/todos" });
    } catch {
      toast.error("Failed to restore todo");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteTodo(id);
      toast.success("Todo deleted permanently");
    } catch {
      toast.error("Failed to delete todo");
    }
  };

  const todos = data?.founds || [];
  const hasData = todos.length > 0;

  return (
    <main className="flex-1 px-10 py-6 max-w-5xl w-full mx-auto animate-fade-in-up">
      <div className="mb-6">
        <Search
          placeholder="Search archived todos..."
          className="max-w-md"
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {isLoading || !hasData ? (
        <EmptyState isLoading={isLoading} message="No archived todos found." />
      ) : (
        <div
          className={`space-y-2 mb-8 transition-opacity duration-200 ${isFetching ? "opacity-50 pointer-events-none" : "opacity-100"}`}
        >
          {todos.map((todo) => (
            <ArchiveCard
              key={todo.id}
              todo={todo}
              onRestore={handleRestore}
              onDelete={handleDelete}
            />
          ))}
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
