"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

const base =
  "inline-flex items-center justify-center gap-2 rounded-full px-5 h-11 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-1 focus:ring-white/30";

const variants: Record<Variant, string> = {
  primary: "bg-white text-black hover:bg-white/90",
  secondary:
    "bg-black text-white border border-white/15 hover:bg-white/5 hover:border-white/25",
  ghost: "bg-transparent text-white/80 hover:text-white",
};

const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "primary", loading, className = "", children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${className}`}
      {...rest}
    >
      {loading ? (
        <span
          aria-hidden
          className="inline-block h-3 w-3 rounded-full border border-current border-t-transparent animate-spin"
        />
      ) : null}
      {children}
    </button>
  );
});

export default Button;
