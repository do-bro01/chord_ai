"use client";

import Link from "next/link";
import Header from "@/components/Header";

export default function Home() {
  return (
    <>
      <Header />
      <main className="flex-1 px-6 py-12 max-w-3xl w-full mx-auto">
        <section className="mb-12">
          <h1
            className="text-4xl font-light tracking-tight mb-3"
            style={{ letterSpacing: "-0.02em" }}
          >
            어떻게 시작할까요?
          </h1>
          <p className="text-sm text-white/50 leading-relaxed">
            코드 진행을 알고 있으면 직접 입력하고, 모르면 음원에서 추출할 수 있습니다.
          </p>
        </section>

        <div className="grid gap-4 sm:grid-cols-2">
          <Link
            href="/input"
            className="group rounded-3xl border border-white/10 bg-[var(--background-elevated)]/50 hover:border-white/25 hover:bg-[var(--background-elevated)]/80 transition-colors px-7 py-8 flex flex-col"
          >
            <p className="text-base text-white font-medium mb-2">
              코드를 알고 있어요
            </p>
            <p className="text-xs text-white/55 leading-relaxed mb-6">
              코드 진행을 직접 입력하고 키 · BPM · 장르를 골라 바로 편곡합니다.
            </p>
            <span className="mt-auto text-xs text-white/40 group-hover:text-white/80 transition-colors">
              직접 입력 →
            </span>
          </Link>

          <Link
            href="/extract"
            className="group rounded-3xl border border-white/10 bg-[var(--background-elevated)]/50 hover:border-white/25 hover:bg-[var(--background-elevated)]/80 transition-colors px-7 py-8 flex flex-col"
          >
            <p className="text-base text-white font-medium mb-2">
              음원에서 추출할게요
            </p>
            <p className="text-xs text-white/55 leading-relaxed mb-2">
              MP3·WAV 등을 업로드하면 코드 진행을 추정해드립니다.
            </p>
            <p className="text-[11px] text-amber-200/70 leading-relaxed mb-6">
              ⚠ 추출 결과는 정확하지 않을 수 있으며 sus·9th·11th 같은 텐션은
              감지되지 않습니다. 추출 후 수정 가능합니다.
            </p>
            <span className="mt-auto text-xs text-white/40 group-hover:text-white/80 transition-colors">
              음원 업로드 →
            </span>
          </Link>
        </div>
      </main>
    </>
  );
}
