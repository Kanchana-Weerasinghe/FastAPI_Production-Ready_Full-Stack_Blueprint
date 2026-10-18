import { MoreVertical } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

type MenuVariant = "danger" | "success" | "default";

export interface MenuOption {
  label: string;
  onClick: () => void;
  icon?: ReactNode;
  variant?: MenuVariant;
}

interface CardProps {
  title: string;
  metadataLabel: string;
  metadataValue: string;
  completed?: boolean;
  actions?: ReactNode;
  icon?: ReactNode;
  menuOptions?: MenuOption[];
  onClick?: () => void;
}

/**
 * A reusable card container that supports a title, metadata, optional icons,
 * and a dropdown menu for actions.
 *
 * @param title - The main heading of the card.
 * @param metadataLabel - Label for the secondary data (e.g., 'Date').
 * @param metadataValue - Value for the secondary data.
 * @param completed - Optional flag for struck-through styling.
 * @param actions - Optional React nodes to replace the default menu.
 * @param icon - Optional React node displayed as a lead icon.
 * @param menuOptions - List of options for the dropdown menu.
 * @param onClick - Optional click handler for the whole card.
 */
export function Card({
  title,
  metadataLabel,
  metadataValue,
  completed = false,
  actions,
  icon,
  menuOptions,
  onClick,
}: CardProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    if (isMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isMenuOpen]);

  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        // Keyboard parity for the clickable card (Enter/Space like a native button).
        if (
          onClick &&
          e.target === e.currentTarget &&
          (e.key === "Enter" || e.key === " ")
        ) {
          e.preventDefault();
          onClick();
        }
      }}
      className="bg-white p-4 rounded-xl shadow-sm border-2 border-brand-200/50 flex items-center gap-4 transition-all group cursor-pointer hover:border-brand-400 relative"
    >
      {icon && (
        <div className="shrink-0 w-8 h-8 flex items-center justify-center">
          {icon}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3
            className={`text-base font-bold truncate ${completed ? "text-brand-600 line-through decoration-brand-400 decoration-2" : "text-brand-600"}`}
          >
            {title}
          </h3>
        </div>
        <div className="flex items-center gap-1.5 mt-1.5">
          <span
            className={`text-xs font-bold uppercase tracking-wider ${completed ? "text-brand-600/60" : "text-brand-300/60"}`}
          >
            {metadataLabel}:
          </span>
          <span
            className={`text-xs font-bold font-mono ${completed ? "text-brand-600/60" : "text-brand-300/60"}`}
          >
            {metadataValue}
          </span>
        </div>
      </div>
      <div className="flex items-center relative" ref={menuRef}>
        {actions ? (
          actions
        ) : (
          <>
            <button
              aria-label="Options"
              onClick={(e) => {
                e.stopPropagation();
                setIsMenuOpen(!isMenuOpen);
              }}
              className={`p-2 rounded-xl transition-all cursor-pointer ${
                isMenuOpen
                  ? "bg-brand-200/50 text-brand-600 opacity-100"
                  : "text-brand-300 hover:text-brand-600 hover:bg-brand-200/50 opacity-0 group-hover:opacity-100"
              }`}
            >
              <MoreVertical size={20} />
            </button>

            {isMenuOpen && menuOptions && (
              <div
                role="menu"
                tabIndex={-1}
                className="absolute right-0 top-full mt-2 w-52 bg-white rounded-xl shadow-xl border-2 border-brand-200/50 z-50 overflow-hidden animate-fade-in-up py-1.5"
                onClick={(e) => e.stopPropagation()}
                onKeyDown={(e) => e.stopPropagation()}
              >
                {menuOptions.map((option, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      option.onClick();
                      setIsMenuOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-4 py-2.5 text-sm font-bold transition-all cursor-pointer group/item
                      ${
                        option.variant === "danger"
                          ? "text-brand-600 hover:text-red-500 hover:bg-red-50"
                          : option.variant === "success"
                            ? "text-brand-600 hover:text-green-600 hover:bg-green-50"
                            : "text-brand-600 hover:bg-brand-100"
                      }`}
                  >
                    <span>{option.label}</span>
                    {option.icon && (
                      <span className="opacity-0 group-hover/item:opacity-100 transition-opacity">
                        {option.icon}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
