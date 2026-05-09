"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import {
  ArrangeRequest,
  Genre,
} from "@/lib/api";

const GENRES: Genre[] = ["City Pop", "Jazz", "Ballad", "Lo-fi", "Bossa Nova"];

const PLACEHOLDER = "C - Am - F - G";

const STORAGE_KEY = "chord_ai.arrange_request";

function parseChords(raw: string): string[] {
  return raw
    .split(/[\s,|/\-]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function ChordInput() {
  const router = useRouter();
  const [chordsRaw, setChordsRaw] = useState("");
  const [keyName, setKeyName] = useState("C major");
  const [bpm, setBpm] = useState(100);
  const [genre, setGenre] = useState<Genre>("Jazz");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = () => {
    const chords = parseChords(chordsRaw);
    if (chords.length === 0) {
      setError("코드를 한 개 이상 입력하세요.");
      return;
    }
    if (chords.length > 64) {
      setError("최대 64마디까지 지원합니다.");
      return;
    }
    if (!keyName.trim()) {
      setError("키를 입력하세요. (예: C major, A minor)");
      return;
    }
    if (!Number.isFinite(bpm) || bpm < 40 || bpm > 240) {
      setError("BPM은 40~240 사이여야 합니다.");
      return;
    }

    setError(null);
    setSubmitting(true);

    const request: ArrangeRequest = {
      current_chords: chords,
      key: keyName.trim(),
      bpm,
      time_signature: "4/4",
      section_size_bars: chords.length,
      options: {
        genre,
        complexity: "보통",
        tension: "보통",
        bass_style: "루트 중심",
        rhythm: "안정적",
      },
    };

    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(request));
    } catch {
      setSubmitting(false);
      setError("브라우저 저장소에 접근할 수 없습니다.");
      return;
    }
    router.push("/arrange");
  };

  return (
    <div className="rounded-3xl border border-white/10 bg-[var(--background-elevated)]/50 px-8 py-10 flex flex-col gap-6">
      <div>
        <label
          htmlFor="chords"
          className="text-xs text-white/60 font-medium tracking-wide block mb-2"
        >
          코드 진행
        </label>
        <textarea
          id="chords"
          rows={3}
          placeholder={PLACEHOLDER}
          value={chordsRaw}
          onChange={(e) => setChordsRaw(e.target.value)}
          className="w-full px-4 py-3 rounded-2xl bg-[var(--background-elevated-2)] border border-white/10 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 transition-colors resize-y"
        />
        <p className="mt-1.5 text-xs text-white/40">
          공백·하이픈·콤마로 구분. 한 칸이 한 마디로 처리됩니다.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Input
          label="키"
          name="key"
          value={keyName}
          onChange={(e) => setKeyName(e.target.value)}
          placeholder="C major"
        />
        <Input
          label="BPM"
          name="bpm"
          type="number"
          min={40}
          max={240}
          value={bpm}
          onChange={(e) => setBpm(Number(e.target.value))}
        />
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="genre"
            className="text-xs text-white/60 font-medium tracking-wide"
          >
            장르
          </label>
          <select
            id="genre"
            value={genre}
            onChange={(e) => setGenre(e.target.value as Genre)}
            className="h-11 px-4 rounded-2xl bg-[var(--background-elevated-2)] border border-white/10 text-sm text-white focus:outline-none focus:border-white/30 transition-colors appearance-none"
          >
            {GENRES.map((g) => (
              <option key={g} value={g} className="bg-black">
                {g}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error ? (
        <p className="text-xs text-red-300">{error}</p>
      ) : null}

      <div className="flex justify-center pt-2">
        <Button
          type="button"
          onClick={onSubmit}
          loading={submitting}
          disabled={submitting}
          className="px-8"
        >
          편곡 시작
        </Button>
      </div>

      <p className="text-center text-xs text-white/30">
        세부 옵션(복잡도·텐션·베이스·리듬·자유 묘사)은 곧 추가됩니다
      </p>
    </div>
  );
}
