"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Header from "@/components/Header";
import Button from "@/components/ui/Button";
import {
  ApiError,
  ArrangeRequest,
  ArrangeResponse,
  arrangeApi,
} from "@/lib/api";

const STORAGE_KEY = "chord_ai.arrange_request";
const BEATS_PER_BAR = 4;

export default function ArrangePage() {
  const router = useRouter();
  const [request, setRequest] = useState<ArrangeRequest | null>(null);
  const [result, setResult] = useState<ArrangeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioLoading, setAudioLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let raw: string | null = null;
    try {
      raw = sessionStorage.getItem(STORAGE_KEY);
    } catch {
      // 접근 불가 → 입력 화면으로
    }
    if (!raw) {
      router.replace("/");
      return;
    }

    let req: ArrangeRequest;
    try {
      req = JSON.parse(raw) as ArrangeRequest;
    } catch {
      router.replace("/");
      return;
    }
    setRequest(req);

    arrangeApi
      .arrange(req)
      .then((res) => setResult(res))
      .catch((err) => {
        if (err instanceof ApiError) setError(err.message);
        else setError("편곡 중 오류가 발생했습니다.");
      })
      .finally(() => setLoading(false));
  }, [router]);

  // audioUrl 변경/언마운트 시 이전 blob URL 해제
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const onPreview = async () => {
    if (!result || !request) return;
    setAudioLoading(true);
    setError(null);
    try {
      const blob = await arrangeApi.preview(
        result.chords,
        request.bpm,
        BEATS_PER_BAR,
      );
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      // 다음 frame에서 자동 재생 시도
      requestAnimationFrame(() => {
        audioRef.current?.play().catch(() => {});
      });
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("미리듣기 생성 실패");
    } finally {
      setAudioLoading(false);
    }
  };

  const onExportPdf = async () => {
    if (!result || !request) return;
    setExportLoading(true);
    setError(null);
    try {
      const blob = await arrangeApi.export({
        chords: result.chords,
        format: "pdf",
        bpm: request.bpm,
        beats_per_bar: BEATS_PER_BAR,
        title: `Arranged-${request.options.genre}`,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Arranged-${request.options.genre}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Export 실패");
    } finally {
      setExportLoading(false);
    }
  };

  const onReset = () => {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    router.push("/");
  };

  return (
    <>
      <Header />
      <main className="flex-1 px-6 py-12 max-w-3xl w-full mx-auto flex flex-col gap-6">
        {loading && (
          <div className="rounded-3xl border border-white/10 bg-[var(--background-elevated)]/50 px-8 py-16 text-center">
            <p className="text-sm text-white/60">편곡 중입니다...</p>
            <p className="text-xs text-white/40 mt-2">
              LLM 응답에 약간 시간이 걸릴 수 있습니다.
            </p>
          </div>
        )}

        {error && (
          <div className="rounded-3xl border border-red-300/30 bg-red-300/5 px-8 py-6">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {result && request && (
          <>
            <div className="rounded-3xl border border-white/10 bg-[var(--background-elevated)]/50 px-8 py-8">
              <p className="text-xs text-white/40 mb-2">원본 코드 진행</p>
              <p className="font-mono text-sm text-white/70 mb-6 break-all">
                {request.current_chords.join(" - ")}
              </p>

              <p className="text-xs text-white/40 mb-2">
                편곡 결과 · {request.key} · {request.bpm} BPM ·{" "}
                {request.options.genre}
              </p>
              <div className="flex flex-wrap gap-2 mb-6">
                {result.chords.map((c, i) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm font-mono text-white/90"
                  >
                    {c}
                  </span>
                ))}
              </div>

              <p className="text-xs text-white/40 mb-1">근거</p>
              <p className="text-sm text-white/70 leading-relaxed mb-4">
                {result.rationale}
              </p>

              {result.warnings.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs text-white/40 mb-1">LLM 경고</p>
                  <ul className="list-disc list-inside text-xs text-white/50 space-y-1">
                    {result.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {result.validation.has_issues && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <p className="text-xs text-white/40 mb-1">룰 검증</p>
                  <p className="text-xs text-white/50">
                    foreign={result.validation.foreign_count} ·
                    music21_fail={result.validation.music21_failures.length} ·
                    unparseable={result.validation.unparseable_count}
                  </p>
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-3 items-center">
              <Button
                onClick={onPreview}
                loading={audioLoading}
                disabled={audioLoading}
              >
                {audioLoading ? "생성 중..." : "▶ 미리듣기"}
              </Button>
              <Button
                variant="secondary"
                onClick={onExportPdf}
                loading={exportLoading}
                disabled={exportLoading}
              >
                {exportLoading ? "생성 중..." : "⬇ PDF 다운로드"}
              </Button>
              <Button
                variant="ghost"
                onClick={onReset}
                className="ml-auto"
              >
                ← 다시 입력
              </Button>
            </div>

            {audioUrl && (
              // eslint-disable-next-line jsx-a11y/media-has-caption
              <audio
                ref={audioRef}
                src={audioUrl}
                controls
                className="w-full mt-2"
              />
            )}
          </>
        )}
      </main>
    </>
  );
}
