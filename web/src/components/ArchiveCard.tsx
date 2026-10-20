import { RotateCcw, Trash2 } from "lucide-react";
import { useState } from "react";

import type { TodoListItem } from "../models/todo";
import { formatDate } from "../utils/helper";
import { Card } from "./Card";
import { Modal } from "./common/Modal";

interface ArchiveCardProps {
  todo: TodoListItem;
  onRestore: (id: string) => void;
  onDelete: (id: string) => void;
}

/**
 * A specialized card component for displaying archived todos.
 * Features restore and permanent delete actions with confirmation modals.
 *
 * @param todo - The archived todo item data.
 * @param onRestore - Callback to restore the todo to active state.
 * @param onDelete - Callback to permanently delete the todo.
 */
export function ArchiveCard({ todo, onRestore, onDelete }: ArchiveCardProps) {
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const menuOptions = [
    {
      label: "Restore",
      onClick: () => onRestore(todo.id),
      icon: <RotateCcw size={16} />,
      variant: "success" as const,
    },
    {
      label: "Permanently delete",
      onClick: () => setIsDeleteModalOpen(true),
      icon: <Trash2 size={16} />,
      variant: "danger" as const,
    },
  ];

  return (
    <>
      <Card
        title={todo.title}
        metadataLabel="Archived on"
        metadataValue={formatDate(todo.updatedAt)}
        menuOptions={menuOptions}
      />
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={() => onDelete(todo.id)}
        title="Permanently Delete?"
        description="You are are going to permanently delete this todo. You won't be able to restore this."
        confirmLabel="Delete Forever"
        variant="danger"
      />
    </>
  );
}
