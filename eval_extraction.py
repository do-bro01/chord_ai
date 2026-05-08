"""추출 정확도 평가용 — 시간축 코드 진행을 그대로 출력한다.

사용법:
    python eval_extraction.py <audio>

main.py와 달리 LLM/악보/오디오 생성을 건너뛰고, 추출 결과만 분석에 적합한
형식으로 콘솔 + JSON 파일로 떨군다.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from audio_analysis import analyze_with_timing, _compress_consecutive


def fmt_time(t: float) -> str:
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:05.2f}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("audio", type=Path)
    p.add_argument("--out", type=Path, default=Path("eval_result.json"))
    args = p.parse_args(argv)

    print(f"[추출 시작] {args.audio}")
    t0 = time.time()
    timed = analyze_with_timing(args.audio)
    elapsed = time.time() - t0
    print(f"[완료] {elapsed:.1f}s, segments={len(timed)}")

    # 시간축 출력
    print("\n--- 시간축 코드 ---")
    for start, end, chord in timed:
        dur = end - start
        print(f"{fmt_time(start)} - {fmt_time(end)}  ({dur:5.2f}s)  {chord}")

    # 압축 출력
    chord_seq = [c for _, _, c in timed]
    compressed = _compress_consecutive(chord_seq)
    print("\n--- 인접 동일 코드 압축 ---")
    print(" - ".join(compressed))
    print(f"\n총 코드 종류: {len(set(compressed))}, 압축 후 길이: {len(compressed)}")

    # JSON 저장
    payload = {
        "audio": str(args.audio),
        "elapsed_sec": elapsed,
        "segments": [
            {"start": s, "end": e, "chord": c} for s, e, c in timed
        ],
        "compressed": compressed,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[저장] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
