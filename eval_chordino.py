"""chordino 추출 평가 — eval_extraction.py의 chordino 버전.

사용법:
    python eval_chordino.py <audio> [--no-demucs] [--no-harte]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from chordino_extractor import analyze_with_timing, _compress_consecutive


def fmt_time(t: float) -> str:
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:05.2f}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("audio", type=Path)
    p.add_argument("--out", type=Path, default=Path("eval_chordino_result.json"))
    p.add_argument("--no-demucs", action="store_true", help="원본 오디오로 직접 (demucs 건너뜀)")
    p.add_argument("--no-harte", action="store_true", help="harte syntax 비활성 (단순 maj/min만)")
    args = p.parse_args(argv)

    print(f"[chordino 추출 시작] {args.audio}")
    t0 = time.time()
    raw = analyze_with_timing(
        args.audio,
        use_demucs_stem=not args.no_demucs,
        use_harte_syntax=not args.no_harte,
    )
    timed = _compress_consecutive(raw)
    elapsed = time.time() - t0
    print(f"[완료] {elapsed:.1f}s, raw={len(raw)} segments, merged={len(timed)} segments")

    # 시간축 출력
    print("\n--- 시간축 코드 (병합 후) ---")
    for start, end, chord in timed:
        dur = end - start
        print(f"{fmt_time(start)} - {fmt_time(end)}  ({dur:5.2f}s)  {chord}")

    # 압축
    chord_seq = [c for _, _, c in timed]
    print(f"\n총 코드 종류: {len(set(chord_seq))}, 진행 길이: {len(chord_seq)}")

    payload = {
        "audio": str(args.audio),
        "elapsed_sec": elapsed,
        "engine": "chordino",
        "use_demucs": not args.no_demucs,
        "use_harte": not args.no_harte,
        "segments": [
            {"start": s, "end": e, "chord": c} for s, e, c in timed
        ],
        "compressed": chord_seq,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[저장] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
