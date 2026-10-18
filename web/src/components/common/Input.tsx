import React, { useId } from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  variant?: "default" | "ghost";
  error?: string;
}

/**
 * A standard form input component with built-in accessibility features (ARIA),
 * error animation states, and consistent typography.
 *
 * @param label - Optional text label displayed above the input.
 * @param variant - Visual style: 'default' or 'ghost'.
 * @param error - Validation error message to display below the input.
 * @param props - Standard HTML input attributes.
 */
export function Input({
  label,
  variant = "default",
  error,
  ...props
}: InputProps) {
  const isGhost = variant === "ghost";
  const errorId = useId();
  const generatedId = useId();
  // Labels must point at the input for screen readers and click-to-focus (WCAG 1.3.1 / 4.1.2).
  const inputId = props.id ?? generatedId;

  return (
    <div className={`flex flex-col w-full ${isGhost ? "gap-0" : "gap-2"}`}>
      {label && (
        <label
          htmlFor={inputId}
          className="text-sm font-bold text-gray-700 uppercase tracking-wider"
        >
          {label}
        </label>
      )}
      <input
        {...props}
        id={inputId}
        aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined}
        className={`w-full transition-all outline-none
                   ${
                     isGhost
                       ? "bg-transparent border-none focus:ring-0"
                       : `border-2 rounded-lg px-4 py-2.5 bg-white shadow-sm focus:shadow-md text-sm text-brand-600 ${
                           error
                             ? "border-red-400 focus:border-red-500"
                             : "border-brand-200 focus:border-brand-400"
                         }`
                   }
                   font-bold
                   placeholder:text-brand-300/30
                   ${props.className || ""}`}
      />
      <div
        className={`grid transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          error
            ? "grid-rows-[1fr] opacity-100 mt-1"
            : "grid-rows-[0fr] opacity-0 mt-0"
        }`}
      >
        <div className="overflow-hidden">
          <span
            id={errorId}
            className="text-xs font-bold text-red-500 block"
            role="alert"
          >
            {error}
          </span>
        </div>
      </div>
    </div>
  );
}
