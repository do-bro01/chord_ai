"use client";

import { useRouter } from "next/navigation";
import { ChangeEvent, DragEvent, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import { ApiError, audioApi } from "@/lib/api";

const ACCEPTED = ["mp3", "wav", "flac", "m4a", "ogg"];
const ACCEPT_ATTR = ACCEPTED.map((e) => `.${e}`).join(",");
const PREFILL_KEY = "chord_ai.prefill_chords";

function isAudio(name: string): boolean {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return ACCEPTED.includes(ext);
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Mp3Extractor() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);

  const acceptFile = (f: File) => {
    if (!isAudio(f.name)) {
      setError("mp3, wav, flac, m4a, ogg 형식만 지원합니다.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(f);
  };

  const onClickArea = () => inputRef.current?.click();

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) acceptFile(f);
    e.target.value = "";
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };
  const onDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
  };
  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) acceptFile(f);
  };

  const onClear = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    setFile(null);
    setError(null);
  };

  const onExtract = async () => {
    if (!file) return;
    setExtracting(true);
    setError(null);
    try {
      const result = await audioApi.extract(file);
      if (!result.chords || result.chords.length === 0) {
        setError("코드 진행을 추출하지 못했습니다. 다른 음원을 시도해주세요.");
        return;
      }
      try {
        sessionStorage.setItem(PREFILL_KEY, JSON.stringify(result.chords));
      } catch {
        setError("브라우저 저장소에 접근할 수 없습니다.");
        return;
      }
      router.push("/input");
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("코드 추출 중 오류가 발생했습니다.");
    } finally {
      setExtracting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-2xl border border-amber-200/30 bg-amber-200/5 px-5 py-4">
        <p className="text-sm text-amber-200/95 font-medium mb-1">정확도 안내</p>
        <ul className="text-xs text-amber-200/70 space-y-1 list-disc list-inside">
          <li>추출된 코드는 부정확할 수 있으며 직접 수정이 필요할 수 있습니다.</li>
          <li>sus 코드, 9th/11th 같은 텐션은 감지되지 않습니다.</li>
          <li>CM7 ↔ Em7, Bm7 ↔ D 같은 상부구조 모호성이 남을 수 있습니다.</li>
          <li>추출 후 코드 입력 화면에서 자유롭게 수정한 뒤 편곡을 진행하세요.</li>
        </ul>
      </div>

      <div
        role="button"
        tabIndex={0}
        onClick={onClickArea}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClickArea();
          }
        }}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`cursor-pointer rounded-3xl border border-dashed bg-[var(--background-elevated)]/50 px-10 py-20 text-center transition-colors ${
          dragOver
            ? "border-white/40 bg-[var(--background-elevated)]/80"
            : "border-white/15 hover:border-white/25"
        }`}
      >
        {file ? (
          <div className="flex flex-col items-center gap-2">
            <p className="text-sm text-white/80">{file.name}</p>
            <p className="text-xs text-white/40">{formatSize(file.size)}</p>
            <button
              type="button"
              onClick={onClear}
              disabled={extracting}
              className="mt-2 text-xs text-white/50 hover:text-white underline disabled:opacity-50"
            >
              다른 파일 선택
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm text-white/60">
              음원 파일을 여기로 드래그하거나 클릭해 업로드하세요
            </p>
            <p className="mt-2 text-xs text-white/30">
              mp3 · wav · flac · m4a · ogg
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTR}
          onChange={onChange}
          className="hidden"
        />
      </div>

      {error ? (
        <p className="text-center text-xs text-red-300">{error}</p>
      ) : null}

      <div className="flex justify-center gap-3">
        <Button
          variant="ghost"
          onClick={() => router.push("/")}
        >
          ← 처음으로
        </Button>
        <Button
          type="button"
          onClick={onExtract}
          loading={extracting}
          disabled={!file || extracting}
          className="px-8"
        >
          {extracting ? "분석 중..." : "코드 추출"}
        </Button>
      </div>

      {extracting ? (
        <p className="text-center text-xs text-white/40">
          음원 분석에는 길이에 따라 수십 초가 걸릴 수 있습니다.
        </p>
      ) : null}
    </div>
  );
}
