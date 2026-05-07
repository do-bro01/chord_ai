import Header from "@/components/Header";
import Uploader from "@/components/Uploader";

export default function Home() {
  return (
    <>
      <Header />
      <main className="flex-1 px-6 py-12 max-w-5xl w-full mx-auto">
        <section className="mb-12">
          <h1 className="text-4xl font-light tracking-tight mb-3" style={{ letterSpacing: "-0.02em" }}>
            음원을 분석하고, 새롭게 편곡합니다.
          </h1>
          <p className="text-sm text-white/50 leading-relaxed whitespace-nowrap">
            mp3, wav, flac 등의 음원을 업로드하면 코드 진행을 추출하고, 원하는 분위기로 편곡한 뒤 악보와 오디오를 생성합니다.
          </p>
        </section>

        <Uploader />
      </main>
    </>
  );
}
