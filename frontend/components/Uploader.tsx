"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";
import Button from "@/components/ui/Button";

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

export default function Uploader() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [converting, setConverting] = useState(false);

  const acceptFile = (f: File) => {
    if (!isAudio(f.name)) {
      setError("mp3, wav, flac, m4a, ogg 형식만 지원합니다.");
      setFile(null);
      return;
    }
    setError(null);
    setNotice(null);
    setFile(f);
  };

  const onClickArea = () => {
    inputRef.current?.click();
  };

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
    setNotice(null);
  };

  const onConvert = async () => {
    if (!file) return;
    setConverting(true);
    setNotice(null);
    // 백엔드 변환 엔드포인트 연결 전 임시 처리.
    await new Promise((r) => setTimeout(r, 600));
    setConverting(false);
    setNotice("코드 추출 · 편곡 기능은 곧 활성화됩니다.");
  };

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
              className="mt-2 text-xs text-white/50 hover:text-white underline"
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
          disabled={!file}
          className="px-8"
        >
          코드로 변환
        </Button>
      </div>

      {notice ? (
        <p className="mt-3 text-center text-xs text-white/50">{notice}</p>
      ) : null}
    </>
  );
}
