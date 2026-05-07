import Header from "@/components/Header";

export default function Home() {
  return (
    <>
      <Header />
      <main className="flex-1 px-6 py-12 max-w-5xl w-full mx-auto">
        <section className="mb-12">
          <h1 className="text-4xl font-light tracking-tight mb-3" style={{ letterSpacing: "-0.02em" }}>
            음원을 분석하고, 새롭게 편곡합니다.
          </h1>
          <p className="text-sm text-white/50 max-w-xl leading-relaxed">
            mp3, wav, flac 등의 음원을 업로드하면 코드 진행을 추출하고,
            원하는 분위기로 편곡한 뒤 악보와 오디오를 생성합니다.
          </p>
        </section>

        <section
          className="rounded-3xl border border-dashed border-white/15 bg-[var(--background-elevated)]/50 px-10 py-20 text-center transition-colors hover:border-white/25"
        >
          <p className="text-sm text-white/60">
            음원 파일을 여기로 드래그하거나 클릭해 업로드하세요
          </p>
          <p className="mt-2 text-xs text-white/30">
            mp3 · wav · flac · m4a · ogg
          </p>
        </section>

        <p className="mt-8 text-center text-xs text-white/30">
          코드 추출 · 편곡 기능은 곧 활성화됩니다
        </p>
      </main>
    </>
  );
}
