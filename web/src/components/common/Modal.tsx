import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

type ModalVariant = "danger" | "default";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ModalVariant;
}

/**
 * A highly reusable overlay component rendered via React Portals.
 * Features focus trapping, body scroll locking, and animated transitions.
 *
 * @param isOpen - Controls the visibility of the modal.
 * @param onClose - Callback triggered on escape or clicking outside/cancel.
 * @param onConfirm - Callback triggered when the primary action is clicked.
 * @param title - Modal heading text.
 * @param description - Descriptive content/body text.
 * @param confirmLabel - Text for the confirm button.
 * @param cancelLabel - Text for the cancel button.
 * @param variant - Visual theme for the confirm button: 'danger' | 'default'.
 */
export function Modal({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-100 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
    >
      <button
        type="button"
        aria-label="Close dialog"
        tabIndex={-1}
        className="absolute inset-0 bg-brand-600/40 backdrop-blur-sm transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] animate-in fade-in cursor-default"
        onClick={onClose}
      />
      <div
        ref={modalRef}
        className="relative bg-white w-full max-w-md rounded-2xl shadow-2xl border-2 border-brand-200/50 p-8
                   animate-in zoom-in-95 slide-in-from-bottom-8
                   duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]"
      >
        <button
          onClick={onClose}
          className="absolute right-4 top-4 p-2 text-brand-300 hover:text-brand-600 hover:bg-brand-100 rounded-xl transition-all cursor-pointer"
        >
          <X size={20} />
        </button>

        <div className="flex flex-col items-center text-center">
          <h2 className="text-2xl font-bold text-brand-600 mb-3">{title}</h2>
          <p className="text-base font-medium text-brand-300/80 leading-relaxed mb-8">
            {description}
          </p>

          <div className="flex gap-4 w-full">
            <button
              onClick={onClose}
              className="flex-1 py-3.5 text-sm font-bold text-gray-700 bg-brand-100 hover:bg-brand-400 hover:text-white rounded-xl transition-all cursor-pointer active:scale-95"
            >
              {cancelLabel}
            </button>
            <button
              onClick={() => {
                onConfirm();
                onClose();
              }}
              className={`flex-1 py-3.5 text-sm font-bold text-gray-700 bg-brand-100 rounded-xl transition-all active:scale-95 cursor-pointer
                ${
                  variant === "danger"
                    ? "hover:bg-red-500 hover:text-white"
                    : "hover:bg-brand-400 hover:text-white"
                }`}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
