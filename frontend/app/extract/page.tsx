import Link from "next/link";
import Header from "@/components/Header";
import Mp3Extractor from "@/components/extract/Mp3Extractor";

export default function ExtractPage() {
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
            음원에서 코드 진행을 추출합니다.
          </h1>
          <p className="text-sm text-white/50 leading-relaxed">
            추출 후 코드 입력 화면에서 결과를 확인 · 수정한 다음 편곡할 수 있습니다.
          </p>
        </section>

        <Mp3Extractor />
      </main>
    </>
  );
}
