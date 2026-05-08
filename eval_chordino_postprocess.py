"""chordino + postprocess 통합 평가 — before/after 비교 출력.

사용법:
    python eval_chordino_postprocess.py <audio>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from chordino_extractor import analyze_with_timing
from chord_postprocess import (
    detect_key,
    postprocess,
    merge_consecutive,
)


def fmt_time(t: float) -> str:
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:05.2f}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("audio", type=Path)
    p.add_argument("--out", type=Path, default=Path("eval_postprocess_result.json"))
    p.add_argument("--min-dur", type=float, default=0.5)
    p.add_argument("--suspect-max-dur", type=float, default=1.5)
    args = p.parse_args(argv)

    print(f"[키 감지] {args.audio}")
    t0 = time.time()
    key_root, key_mode = detect_key(args.audio)
    print(f"  → {key_root} {key_mode}  ({time.time() - t0:.1f}s)")

    print(f"[chordino 추출]")
    t0 = time.time()
    raw = analyze_with_timing(args.audio, use_demucs_stem=True, use_harte_syntax=True)
    print(f"  → raw {len(raw)} segments  ({time.time() - t0:.1f}s)")

    print(f"[후처리: min_dur={args.min_dur}, suspect_max={args.suspect_max_dur}]")
    raw_merged = merge_consecutive(raw)
    processed = postprocess(
        raw,
        key_root=key_root,
        key_mode=key_mode,
        min_dur=args.min_dur,
        suspect_max_dur=args.suspect_max_dur,
    )
    print(f"  → before merge: {len(raw)} → after merge: {len(raw_merged)} → after postprocess: {len(processed)} segments")

    # before/after diff 출력
    print("\n--- BEFORE (chordino raw, merged) ---")
    for s, e, c in raw_merged:
        print(f"{fmt_time(s)} - {fmt_time(e)}  ({e - s:5.2f}s)  {c}")

    print("\n--- AFTER (postprocessed) ---")
    for s, e, c in processed:
        print(f"{fmt_time(s)} - {fmt_time(e)}  ({e - s:5.2f}s)  {c}")

    print("\n--- 압축 진행 ---")
    print("BEFORE:", " - ".join(c for _, _, c in raw_merged))
    print()
    print("AFTER: ", " - ".join(c for _, _, c in processed))

    payload = {
        "audio": str(args.audio),
        "key": f"{key_root} {key_mode}",
        "min_dur": args.min_dur,
        "suspect_max_dur": args.suspect_max_dur,
        "before": [{"start": s, "end": e, "chord": c} for s, e, c in raw_merged],
        "after": [{"start": s, "end": e, "chord": c} for s, e, c in processed],
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[저장] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
