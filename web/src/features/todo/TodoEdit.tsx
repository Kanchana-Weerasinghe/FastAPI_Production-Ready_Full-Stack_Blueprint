import { useForm } from "@tanstack/react-form";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { ArrowLeft, CheckCircle, Plus, Save } from "lucide-react";
import { useState } from "react";
import { useRef } from "react";
import { toast } from "sonner";

import { Button } from "../../components/common/Button";
import { Input } from "../../components/common/Input";
import { CompactAssetCard } from "../../components/CompactAssetCard";
import {
  ALLOWED_EXTENSIONS,
  getAttachmentIcon,
} from "../../constants/attachments.constants";
import {
  useRemoveAttachment,
  useUpdateTodo,
  useUploadAttachment,
} from "../../hooks/mutations/todos";
import { useTodo } from "../../hooks/queries/todos";
import type { Attachment } from "../../models/attachment";
import { type Todo, todoSchema } from "../../models/todo";
import {
  formatDate,
  formatFileSize,
  getDownloadUrl,
  getErrorMessage,
  validateFileSize,
} from "../../utils/helper";

/**
 * The Todo Edit feature page.
 * Provides a rich form to update todo content and manage attachments,
 * with real-time validation and file upload support.
 */
export function TodoEdit() {
  const { todoId } = useParams({ from: "/_authenticated/todo/$todoId/edit" });
  const { data: todo, isLoading } = useTodo(todoId);

  if (isLoading || !todo) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-brand-400"></div>
      </div>
    );
  }

  return <TodoEditForm todo={todo} todoId={todoId} />;
}

interface TodoEditFormProps {
  todo: Todo;
  todoId: string;
}

function TodoEditForm({ todo, todoId }: TodoEditFormProps) {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { mutateAsync: updateTodo } = useUpdateTodo(todoId);
  const { mutateAsync: removeAttachment } = useRemoveAttachment(todoId);
  const { mutateAsync: uploadAttachment, isPending: isUploading } =
    useUploadAttachment(todoId);

  const [activeField, setActiveField] = useState<string | null>(null);
  const [newAttachmentIds, setNewAttachmentIds] = useState<string[]>([]);
  const [removedAttachmentIds, setRemovedAttachmentIds] = useState<string[]>(
    [],
  );
  const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>(
    [],
  );

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!validateFileSize(file)) {
      toast.error("File too large", {
        description: "Max 50MB data is allowed.",
      });
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    try {
      const uploadedAttachment = await uploadAttachment(file);
      setNewAttachmentIds((prev) => [...prev, uploadedAttachment.id]);
      setPendingAttachments((prev) => [...prev, uploadedAttachment]);
      toast.success("File uploaded and ready to save");
    } catch {
      toast.error("Failed to upload file");
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const removePendingAttachment = (index: number) => {
    setNewAttachmentIds((prev) => prev.filter((_, i) => i !== index));
    setPendingAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDeleteAttachment = async (fileId: string) => {
    try {
      await removeAttachment(fileId);
      setRemovedAttachmentIds((prev) => [...prev, fileId]);
      toast.success("Attachment removed");
    } catch {
      toast.error("Failed to remove attachment");
    }
  };

  const handleDownload = (fileId: string) => {
    window.open(getDownloadUrl(fileId), "_blank");
  };

  const form = useForm({
    defaultValues: {
      title: todo.title,
      description: todo.description || "",
    },
    onSubmit: async ({ value }) => {
      try {
        await updateTodo({
          ...value,
          attachmentIds: [
            ...todo.attachments
              .filter((a) => !removedAttachmentIds.includes(a.id))
              .map((a) => a.id),
            ...newAttachmentIds,
          ],
        });
        toast.success("Todo updated successfully");
        navigate({
          to: "/todos",
        });
      } catch {
        toast.error("Failed to update todo");
      }
    },
  });

  const primaryButtonStyle =
    "px-6 py-2.5 rounded-xl text-base shadow-md hover:shadow-lg transition-all shrink-0 font-bold flex items-center justify-center gap-2";

  return (
    <main className="flex-1 px-10 py-6 max-w-5xl w-full mx-auto animate-fade-in-up">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          e.stopPropagation();
          form.handleSubmit();
        }}
      >
        <div className="flex items-center justify-between mb-6">
          <Link
            to="/todo/$todoId"
            params={{ todoId }}
            activeOptions={{ exact: true }}
          >
            <Button
              type="button"
              variant="primary"
              className={primaryButtonStyle}
            >
              <ArrowLeft size={18} />
              Back
            </Button>
          </Link>

          <form.Subscribe
            selector={(state) => [state.canSubmit, state.isSubmitting]}
          >
            {([canSubmit, isSubmitting]) => (
              <Button
                type="submit"
                disabled={!canSubmit || isSubmitting}
                variant="primary"
                className={`${primaryButtonStyle} disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <Save size={18} />
                {isSubmitting ? "Saving..." : "Save"}
              </Button>
            )}
          </form.Subscribe>
        </div>

        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border-2 border-brand-200/50">
          <div className="px-8 pb-8 pt-6">
            <div className="flex items-start justify-between gap-4 mb-2">
              <div className="flex-1 min-w-0">
                <form.Field
                  name="title"
                  validators={{
                    onChangeAsync: todoSchema.shape.title,
                    onChangeAsyncDebounceMs: 300,
                  }}
                >
                  {(field) => (
                    <div className="mb-0 w-full">
                      <Input
                        variant="ghost"
                        type="text"
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onFocus={() => setActiveField(field.name)}
                        onBlur={() => {
                          field.handleBlur();
                          setActiveField(null);
                        }}
                        onChange={(e) => field.handleChange(e.target.value)}
                        className="text-5xl font-bold text-gray-700 placeholder:text-gray-400/60 pt-0 pb-2 leading-normal border-none bg-transparent outline-none focus:ring-0 shadow-none px-0"
                        placeholder="Title"
                        error={
                          activeField === field.name &&
                          !field.state.meta.isValidating
                            ? getErrorMessage(field.state.meta.errors[0])
                            : undefined
                        }
                      />
                    </div>
                  )}
                </form.Field>
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

            <form.Field
              name="description"
              validators={{
                onChangeAsync: todoSchema.shape.description.unwrap(),
                onChangeAsyncDebounceMs: 300,
              }}
            >
              {(field) => {
                return (
                  <div className="mb-4 relative">
                    {activeField === field.name &&
                      !field.state.meta.isValidating &&
                      field.state.meta.errors[0] && (
                        <span className="absolute -top-6 right-0 text-xs font-bold text-red-500 animate-slide-down">
                          {getErrorMessage(field.state.meta.errors[0])}
                        </span>
                      )}
                    <textarea
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onFocus={() => setActiveField(field.name)}
                      onBlur={() => {
                        field.handleBlur();
                        setActiveField(null);
                      }}
                      onChange={(e) => field.handleChange(e.target.value)}
                      placeholder="Tell your story..."
                      className={`w-full min-h-[300px] outline-none py-0 transition-all bg-transparent font-bold text-gray-700 text-xl placeholder:text-gray-400/60 resize-none leading-relaxed`}
                    />
                  </div>
                );
              }}
            </form.Field>

            <div className="mb-2">
              <div className="flex flex-col gap-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {todo.attachments
                    .filter((file) => !removedAttachmentIds.includes(file.id))
                    .map((file) => (
                      <CompactAssetCard
                        key={file.id}
                        name={file.fileName}
                        type={file.fileType}
                        size={formatFileSize(file.fileSize)}
                        date={formatDate(file.createdAt)}
                        iconUrl={getAttachmentIcon(file.fileName)}
                        onDownload={() => handleDownload(file.id)}
                        onDelete={() => handleDeleteAttachment(file.id)}
                      />
                    ))}
                  {pendingAttachments.map((file, index) => (
                    <CompactAssetCard
                      key={file.id}
                      name={file.fileName}
                      type={file.fileType}
                      size={formatFileSize(file.fileSize)}
                      date={formatDate(file.createdAt)}
                      iconUrl={getAttachmentIcon(file.fileName)}
                      onDownload={() => handleDownload(file.id)}
                      onDelete={() => removePendingAttachment(index)}
                    />
                  ))}
                </div>

                <div className="flex items-center gap-4">
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept={ALLOWED_EXTENSIONS.join(",")}
                    onChange={handleFileChange}
                  />
                  <Button
                    type="button"
                    variant="primary"
                    className={primaryButtonStyle}
                    disabled={isUploading}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Plus size={20} />
                    {isUploading ? "UPLOADING..." : "ADD ATTACHMENT"}
                  </Button>
                </div>
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
      </form>
    </main>
  );
}
