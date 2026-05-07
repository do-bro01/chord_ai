import Link from "next/link";

export default function Logo({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/"
      className={`font-light tracking-tight text-white/95 ${className}`}
      style={{ letterSpacing: "-0.02em" }}
    >
      <span className="text-base">chord</span>
      <span className="text-base text-white/50">_ai</span>
    </Link>
  );
}
