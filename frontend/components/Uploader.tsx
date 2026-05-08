"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import { ApiError, audioApi, Bar } from "@/lib/api";

const ACCEPTED = ["mp3", "wav", "flac", "m4a", "ogg"];
const ACCEPT_ATTR = ACCEPTED.map((e) => `.${e}`).join(",");

function isAudio(name: string): boolean {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return ACCEPTED.includes(ext);
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec - m * 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const BARS_PER_ROW = 4;

function chunkBars(bars: Bar[], size: number): Bar[][] {
  const rows: Bar[][] = [];
  for (let i = 0; i < bars.length; i += size) {
    rows.push(bars.slice(i, i + size));
  }
  return rows;
}

export default function Uploader() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [converting, setConverting] = useState(false);
  const [chords, setChords] = useState<string[] | null>(null);
  const [bars, setBars] = useState<Bar[] | null>(null);

  const acceptFile = (f: File) => {
    if (!isAudio(f.name)) {
      setError("mp3, wav, flac, m4a, ogg 형식만 지원합니다.");
      setFile(null);
      return;
    }
    setError(null);
    setChords(null);
    setBars(null);
    setFile(f);
  };

  const onClickArea = () => {
    if (chords) return;
    inputRef.current?.click();
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) acceptFile(f);
    e.target.value = "";
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    if (chords) return;
    e.preventDefault();
    setDragOver(true);
  };

  const onDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    if (chords) return;
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) acceptFile(f);
  };

  const onClear = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    setFile(null);
    setError(null);
    setChords(null);
    setBars(null);
  };

  const onReset = () => {
    setFile(null);
    setError(null);
    setChords(null);
    setBars(null);
  };

  const onConvert = async () => {
    if (!file) return;
    setConverting(true);
    setError(null);
    try {
      const result = await audioApi.extract(file);
      setChords(result.chords);
      setBars(result.bars);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("코드 추출 중 오류가 발생했습니다.");
    } finally {
      setConverting(false);
    }
  };

  if (chords) {
    const rows = bars && bars.length > 0 ? chunkBars(bars, BARS_PER_ROW) : [];
    return (
      <div className="flex flex-col gap-6">
        <div className="rounded-3xl border border-white/10 bg-[var(--background-elevated)]/50 px-8 py-10">
          <p className="text-xs text-white/40 mb-2">추출된 코드 진행</p>
          <p className="text-xs text-white/50 mb-6 truncate">{file?.name}</p>

          {rows.length > 0 ? (
            <div className="flex flex-col gap-1.5 font-mono text-sm">
              {rows.map((row, ri) => (
                <div
                  key={ri}
                  className="flex items-center gap-3 text-white/85"
                >
                  <span className="shrink-0 w-12 text-xs text-white/35 tabular-nums">
                    {formatTime(row[0].start)}
                  </span>
                  <div className="flex-1 grid grid-cols-4 items-center">
                    {row.map((bar, idx) => (
                      <div
                        key={bar.index}
                        className="flex items-center min-w-0"
                        title={`마디 ${bar.index} (${bar.start.toFixed(2)}s~${bar.end.toFixed(2)}s)`}
                      >
                        <span className="text-white/25 shrink-0 px-2">|</span>
                        <div className="flex-1 grid grid-cols-4 items-center">
                          {bar.beats.map((slot, i) => (
                            <span
                              key={i}
                              className="text-center whitespace-nowrap overflow-hidden text-ellipsis"
                            >
                              {slot.chord ?? (
                                <span className="text-white/15">·</span>
                              )}
                            </span>
                          ))}
                        </div>
                        {idx === row.length - 1 && (
                          <span className="text-white/25 shrink-0 px-2">|</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {chords.map((c, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm font-mono text-white/90"
                >
                  {c}
                </span>
              ))}
            </div>
          )}

          <p className="mt-6 text-xs text-white/30">
            총 {bars?.length ?? 0}마디 · {chords.length}개 코드 변경
          </p>
        </div>
        <div className="flex justify-center">
          <Button type="button" variant="secondary" onClick={onReset} className="px-8">
            다른 음원 분석하기
          </Button>
        </div>
        <p className="text-center text-xs text-white/30">
          편곡 · 악보 · 오디오 생성 기능은 곧 활성화됩니다
        </p>
      </div>
    );
  }

  return (
    <>
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
              disabled={converting}
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
        <p className="mt-3 text-center text-xs text-red-300">{error}</p>
      ) : null}

      <div className="mt-6 flex justify-center">
        <Button
          type="button"
          onClick={onConvert}
          loading={converting}
          disabled={!file || converting}
          className="px-8"
        >
          {converting ? "분석 중..." : "코드로 변환"}
        </Button>
      </div>

      {converting ? (
        <p className="mt-3 text-center text-xs text-white/40">
          음원 분석에는 길이에 따라 수십 초가 걸릴 수 있습니다
        </p>
      ) : null}
    </>
  );
}
