import React from "react";

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

/**
 * A highly customizable, accessible button component with built-in
 * state animations and brand-consistent styling.
 *
 * @param variant - Visual style variant: 'primary' | 'secondary' | 'outline' | 'ghost'.
 * @param className - Optional CSS classes for customization.
 * @param children - Button content (text or icons).
 * @param props - Standard HTML button attributes.
 */
export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonProps) {
  const isGhost = variant === "ghost";

  const baseStyles = `font-bold transition-all active:scale-[0.98] cursor-pointer flex items-center gap-2 justify-center ${
    !isGhost ? "px-6 py-2 rounded-lg" : ""
  }`;

  const variants = {
    primary: "bg-brand-400 text-white hover:opacity-90 shadow-md",
    secondary: "bg-brand-600 text-white hover:opacity-90 shadow-md",
    outline:
      "bg-white border-2 border-brand-400 text-brand-400 hover:bg-brand-400 hover:text-white",
    ghost: "bg-transparent",
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
