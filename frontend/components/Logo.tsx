import Link from "next/link";

export default function Logo({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/"
      className={`font-light tracking-tight text-white/95 ${className || "text-base"}`}
      style={{ letterSpacing: "-0.02em" }}
    >
      <span>Chord</span>
      <span className="text-white/50">_AI</span>
    </Link>
  );
}
