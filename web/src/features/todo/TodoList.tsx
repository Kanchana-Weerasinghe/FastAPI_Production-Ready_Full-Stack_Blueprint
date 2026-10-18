import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "../../components/common/Button";
import { Pagination } from "../../components/common/Pagination";
import { EmptyState } from "../../components/Empty";
import { Search } from "../../components/Search";
import { TodoCard } from "../../components/TodoCard";
import {
  useToggleArchiveTodo,
  useUpdateTodoGeneric,
} from "../../hooks/mutations/todos";
import { useTodos } from "../../hooks/queries/todos";
import { useDebounce } from "../../hooks/shared/useDebounce";

/**
 * The Todo List feature page.
 * The main dashboard where users can view, filter, and manage their active todos.
 * Supports search, pagination, and quick status toggling.
 */
export function TodoList() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearch = useDebounce(searchTerm, 500);
  const { data, isLoading, isFetching } = useTodos({
    title: debouncedSearch,
    page,
  });
  const { mutateAsync: toggleArchive } = useToggleArchiveTodo();
  const { mutateAsync: updateTodo } = useUpdateTodoGeneric();

  const handleArchive = async (id: string) => {
    try {
      await toggleArchive(id);
      toast.success("Todo moved to archives");
      navigate({ to: "/archives" });
    } catch {
      toast.error("Failed to archive todo");
    }
  };

  const handleToggle = async (id: string) => {
    const todo = data?.founds.find((t) => t.id === id);
    if (!todo) return;

    try {
      await updateTodo({
        todoId: id,
        data: { isCompleted: !todo.isCompleted },
      });
      toast.success(
        todo.isCompleted ? "Marked as pending" : "Marked as completed",
      );
    } catch {
      toast.error("Failed to update status");
    }
  };

  const todos = data?.founds || [];
  const hasData = todos.length > 0;

  return (
    <main className="flex-1 px-10 py-6 max-w-5xl w-full mx-auto animate-fade-in-up">
      <div className="flex items-center justify-between gap-4 mb-6">
        <Search
          placeholder="Search todos..."
          className="max-w-md"
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setPage(1);
          }}
        />
        <Link to="/todo/new">
          <Button className="px-6 py-2.5 rounded-xl text-base shadow-md hover:shadow-lg transition-all shrink-0">
            Add Todo
          </Button>
        </Link>
      </div>

      {isLoading || !hasData ? (
        <EmptyState
          isLoading={isLoading}
          message="No todos found."
          subMessage="Create your first todo to get started!"
        />
      ) : (
        <div
          className={`space-y-2 mb-8 transition-opacity duration-200 ${isFetching ? "opacity-50 pointer-events-none" : "opacity-100"}`}
        >
          {todos.map((todo) => (
            <TodoCard
              key={todo.id}
              todo={todo}
              onToggle={handleToggle}
              onDelete={handleArchive}
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
