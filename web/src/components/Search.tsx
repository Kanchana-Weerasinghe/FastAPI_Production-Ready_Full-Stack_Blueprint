import { Search as SearchIcon } from "lucide-react";
import React from "react";

interface SearchProps extends React.InputHTMLAttributes<HTMLInputElement> {
  placeholder?: string;
}

/**
 * A branded search input field with an integrated icon.
 * Supports all standard HTML input attributes for seamless integration with forms.
 *
 * @param placeholder - Custom placeholder text. Defaults to "Search...".
 * @param props - Standard HTML input attributes.
 */
export function Search({ placeholder = "Search...", ...props }: SearchProps) {
  return (
    <div className={`relative group w-full ${props.className || ""}`}>
      <SearchIcon
        className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-600/40 group-focus-within:text-brand-400 transition-colors"
        size={18}
      />
      <input
        {...props}
        type="text"
        placeholder={placeholder}
        className="w-full bg-white border-2 border-brand-200 rounded-xl py-2.5 pl-11 pr-4 text-sm font-bold outline-none focus:border-brand-400 transition-all placeholder:text-brand-300/30 shadow-sm focus:shadow-md"
      />
    </div>
  );
}
