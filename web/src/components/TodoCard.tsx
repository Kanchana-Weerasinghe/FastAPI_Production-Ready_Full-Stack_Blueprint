import { useNavigate } from "@tanstack/react-router";
import { CheckCircle, Edit3, Trash2, XCircle } from "lucide-react";
import { useState } from "react";

import type { TodoListItem } from "../models/todo";
import { formatDate } from "../utils/helper";
import { Card } from "./Card";
import { Modal } from "./common/Modal";

interface TodoCardProps {
  todo: TodoListItem;
  onToggle?: (id: string) => void;
  onDelete?: (id: string) => void;
}

/**
 * A specialized card for todo items.
 * Handles navigation to details/edit pages and provides quick actions for
 * completion and archiving.
 *
 * @param todo - The todo item data.
 * @param onToggle - Callback for toggling completion status.
 * @param onDelete - Callback for archiving/deleting the todo.
 */
export function TodoCard({ todo, onToggle, onDelete }: TodoCardProps) {
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const navigate = useNavigate();

  const menuOptions = [
    {
      label: "Edit",
      onClick: () => {
        navigate({
          to: "/todo/$todoId/edit",
          params: { todoId: todo.id },
        });
      },
      icon: <Edit3 size={16} />,
    },
    {
      label: todo.isCompleted ? "Mark as incomplete" : "Mark as completed",
      onClick: () => {
        onToggle?.(todo.id);
      },
      icon: todo.isCompleted ? (
        <XCircle size={16} />
      ) : (
        <CheckCircle size={16} />
      ),
      variant: "success" as const,
    },
    {
      label: "Delete",
      onClick: () => {
        setIsDeleteModalOpen(true);
      },
      icon: <Trash2 size={16} />,
      variant: "danger" as const,
    },
  ];

  return (
    <>
      <Card
        title={todo.title}
        metadataLabel="Last Modified"
        metadataValue={formatDate(todo.updatedAt)}
        completed={todo.isCompleted}
        menuOptions={menuOptions}
        onClick={() =>
          navigate({
            to: "/todo/$todoId",
            params: { todoId: todo.id },
          })
        }
      />
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={() => onDelete?.(todo.id)}
        title="Delete Todo?"
        description="This todo will be deleted after a month of inactivity. You can always restore this todo from the archive page."
        confirmLabel="Delete"
        variant="danger"
      />
    </>
  );
}
