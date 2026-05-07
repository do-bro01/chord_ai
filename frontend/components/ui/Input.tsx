"use client";

import { InputHTMLAttributes, forwardRef } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { label, hint, error, className = "", id, ...rest },
  ref,
) {
  const inputId = id || rest.name;
  return (
    <div className="flex flex-col gap-1.5">
      {label ? (
        <label
          htmlFor={inputId}
          className="text-xs text-white/60 font-medium tracking-wide"
        >
          {label}
        </label>
      ) : null}
      <input
        id={inputId}
        ref={ref}
        className={`h-11 px-4 rounded-2xl bg-[var(--background-elevated-2)] border border-white/10 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 transition-colors ${className}`}
        {...rest}
      />
      {error ? (
        <span className="text-xs text-red-400/90">{error}</span>
      ) : hint ? (
        <span className="text-xs text-white/40">{hint}</span>
      ) : null}
    </div>
  );
});

export default Input;
