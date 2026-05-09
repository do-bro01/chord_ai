import ChordInput from "@/components/chord/ChordInput";
import Header from "@/components/Header";

export default function Home() {
  return (
    <>
      <Header />
      <main className="flex-1 px-6 py-12 max-w-3xl w-full mx-auto">
        <section className="mb-12">
          <h1 className="text-4xl font-light tracking-tight mb-3" style={{ letterSpacing: "-0.02em" }}>
            코드 진행을 입력하면, 새롭게 편곡합니다.
          </h1>
          <p className="text-sm text-white/50 leading-relaxed">
            원하는 코드 진행과 키·BPM·장르를 입력하면 LLM이 리하모니제이션·텐션·치환을 적용한 결과를 들려드립니다.
          </p>
        </section>

        <ChordInput />
      </main>
    </>
  );
}
