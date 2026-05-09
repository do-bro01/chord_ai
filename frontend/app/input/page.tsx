import Link from "next/link";
import ChordInput from "@/components/chord/ChordInput";
import Header from "@/components/Header";

export default function InputPage() {
  return (
    <>
      <Header />
      <main className="flex-1 px-6 py-12 max-w-3xl w-full mx-auto">
        <section className="mb-8">
          <Link
            href="/"
            className="text-xs text-white/40 hover:text-white/70 transition-colors"
          >
            ← 처음으로
          </Link>
          <h1
            className="mt-4 text-4xl font-light tracking-tight mb-3"
            style={{ letterSpacing: "-0.02em" }}
          >
            코드 진행을 입력하세요.
          </h1>
          <p className="text-sm text-white/50 leading-relaxed">
            키 · BPM · 장르를 함께 입력하면 LLM이 리하모니제이션 · 텐션 · 치환을
            적용한 결과를 보여드립니다.
          </p>
        </section>

        <ChordInput />
      </main>
    </>
  );
}
