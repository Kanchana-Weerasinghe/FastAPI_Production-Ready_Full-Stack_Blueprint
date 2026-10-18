import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { ArrowLeft, Check, CheckCircle, Edit3, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "../../components/common/Button";
import { Modal } from "../../components/common/Modal";
import { CompactAssetCard } from "../../components/CompactAssetCard";
import { getAttachmentIcon } from "../../constants/attachments.constants";
import {
  useToggleArchiveTodo,
  useUpdateTodo,
} from "../../hooks/mutations/todos";
import { useTodo } from "../../hooks/queries/todos";
import { formatDate, formatFileSize, getDownloadUrl } from "../../utils/helper";

/**
 * The Todo Detail feature page.
 * Displays comprehensive information about a specific todo, including
 * its status, description, and attached assets.
 */
export function TodoDetail() {
  const { todoId } = useParams({ from: "/_authenticated/todo/$todoId/" });
  const navigate = useNavigate();
  const { data: todo, isLoading } = useTodo(todoId);
  const { mutateAsync: archiveTodo } = useToggleArchiveTodo();
  const { mutateAsync: updateTodo } = useUpdateTodo(todoId);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const handleDelete = async () => {
    try {
      await archiveTodo(todoId);
      toast.success("Todo moved to archives");
      navigate({ to: "/todos" });
    } catch {
      toast.error("Failed to archive todo");
    } finally {
      setIsDeleteModalOpen(false);
    }
  };

  const handleToggleComplete = async () => {
    if (!todo) return;
    try {
      await updateTodo({ isCompleted: !todo.isCompleted });
      toast.success(
        todo.isCompleted ? "Marked as pending" : "Marked as completed",
      );
      navigate({ to: "/todos" });
    } catch {
      toast.error("Failed to update status");
    }
  };

  const handleDownload = (fileId: string) => {
    window.open(getDownloadUrl(fileId), "_blank");
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-400"></div>
      </div>
    );
  }

  if (!todo) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-brand-300 py-20">
        <p className="text-xl font-medium">Todo not found.</p>
        <Link
          to="/todos"
          className="mt-4 text-brand-400 hover:underline font-bold"
        >
          Go back to list
        </Link>
      </div>
    );
  }

  const primaryButtonStyle =
    "px-6 py-2.5 rounded-xl text-base shadow-md hover:shadow-lg transition-all shrink-0";
  const outlineButtonStyle =
    "px-6 py-2 rounded-xl text-base shadow-md hover:shadow-lg transition-all shrink-0";

  return (
    <>
      <main className="flex-1 px-10 py-6 max-w-5xl w-full mx-auto animate-fade-in-up">
        <div className="flex items-center justify-between mb-6">
          <Link to="/todos">
            <Button
              className={`${primaryButtonStyle} bg-brand-200/50 text-gray-700 hover:bg-brand-400 hover:text-white border-none transition-all flex items-center justify-center gap-2`}
            >
              <ArrowLeft size={18} />
              Back
            </Button>
          </Link>

          <Link to="/todo/$todoId/edit" params={{ todoId }}>
            <Button variant="outline" className={outlineButtonStyle}>
              <Edit3 size={18} />
              Edit
            </Button>
          </Link>
        </div>

        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border-2 border-brand-200/50">
          <div className="px-8 pb-8 pt-6">
            <div className="flex items-start justify-between gap-4 mb-2">
              <div className="flex-1 min-w-0">
                <div className="mb-0 w-full">
                  <input
                    type="text"
                    value={todo.title}
                    readOnly
                    className="text-5xl font-bold text-gray-700 pt-0 pb-2 leading-normal bg-transparent border-none outline-none w-full focus:ring-0"
                  />
                </div>
              </div>

              <div className="shrink-0 mt-2">
                <div
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl border-2 font-bold text-sm transition-all ${
                    todo.isCompleted
                      ? "bg-green-50 border-green-200 text-green-600"
                      : "bg-brand-100 border-brand-200/50 text-brand-400"
                  }`}
                >
                  <CheckCircle size={18} />
                  <span>{todo.isCompleted ? "Completed" : "Pending"}</span>
                </div>
              </div>
            </div>

            <div className="mb-4">
              <div className="w-full min-h-[300px] py-0 bg-transparent font-bold text-gray-700 text-xl whitespace-pre-wrap leading-relaxed">
                {todo.description || (
                  <span className="text-gray-400/60">Tell your story...</span>
                )}
              </div>
            </div>

            <div className="mb-2">
              <div className="flex flex-col gap-6">
                {todo.attachments && todo.attachments.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {todo.attachments.map((file) => (
                      <CompactAssetCard
                        key={file.id}
                        name={file.fileName}
                        type={file.fileType}
                        size={formatFileSize(file.fileSize)}
                        date={formatDate(file.createdAt || todo.updatedAt)}
                        iconUrl={getAttachmentIcon(file.fileName)}
                        onDownload={() => handleDownload(file.id)}
                        readOnly={true}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-brand-100/50 border-t-2 border-brand-200/50 px-10 py-4 flex flex-wrap items-center gap-x-12 gap-y-4 text-brand-600/60 font-bold text-sm font-mono">
            <div className="flex items-center gap-2">
              <span className="uppercase tracking-widest opacity-60">
                Created:
              </span>
              <span className="text-brand-600">
                {formatDate(todo.createdAt)}
              </span>
            </div>
            <div className="flex items-center gap-2 border-l-2 border-brand-200 pl-8">
              <span className="uppercase tracking-widest opacity-60">
                Last Modified:
              </span>
              <span className="text-brand-600">
                {formatDate(todo.updatedAt)}
              </span>
            </div>
          </div>
        </div>

        <div className="mt-6 mb-20 flex justify-end gap-5">
          <Button
            variant="primary"
            className={`${primaryButtonStyle} bg-brand-200/50 text-gray-700 hover:bg-red-500 hover:text-white border-none group transition-all flex items-center justify-center gap-0 hover:gap-3`}
            onClick={() => setIsDeleteModalOpen(true)}
          >
            <span className="font-bold uppercase tracking-wider">Delete</span>
            <Trash2
              size={18}
              className="w-0 group-hover:w-5 opacity-0 group-hover:opacity-100 transition-all duration-300 transform scale-0 group-hover:scale-100"
            />
          </Button>
          <Button
            variant="primary"
            onClick={handleToggleComplete}
            className={`${primaryButtonStyle} bg-brand-200/50 text-gray-700 ${
              todo.isCompleted ? "hover:bg-brand-400" : "hover:bg-green-600"
            } hover:text-white border-none group transition-all flex items-center justify-center gap-0 hover:gap-3`}
          >
            <span className="font-bold uppercase tracking-wider">
              {todo.isCompleted ? "Mark as Pending" : "Mark as Completed"}
            </span>
            <Check
              size={20}
              className="w-0 group-hover:w-6 opacity-0 group-hover:opacity-100 transition-all duration-300 transform scale-0 group-hover:scale-100"
            />
          </Button>
        </div>
      </main>

      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleDelete}
        title="Delete Todo?"
        description="This todo will be delete after a month of inactivity along with assets and attachment. You can always restore this todo from the archive page."
        confirmLabel="Delete"
        variant="danger"
      />
    </>
  );
}
