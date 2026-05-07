import { HTMLAttributes } from "react";

interface Props extends HTMLAttributes<HTMLDivElement> {}

export default function Card({ className = "", children, ...rest }: Props) {
  return (
    <div
      className={`bg-[var(--background-elevated)] border border-white/8 rounded-3xl ${className}`}
      style={{ borderColor: "rgba(255,255,255,0.08)" }}
      {...rest}
    >
      {children}
    </div>
  );
}
