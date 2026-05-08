"""chordino + 후처리 + 베이스 보정 통합 평가.

흐름:
  1. 키 감지
  2. chordino 추출 (demucs harmonic stem)
  3. 짧은 잡음 필터 + 다이어토닉 보정
  4. 베이스 검출 + 베이스 보정 (CM7↔Em7, slash 등)
  5. 인접 동일 코드 병합

각 단계 전후를 비교해서 어떤 단계가 어떤 효과를 냈는지 분석.

사용법(프로젝트 루트에서):
    python scripts/eval_full_pipeline.py "test_mp3/곡.mp3"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# scripts/에서 실행되므로 부모 디렉토리(프로젝트 루트)를 import path에 추가
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from chordino_extractor import analyze_with_timing
from chord_postprocess import (
    detect_key,
    filter_short_segments,
    apply_diatonic_correction,
    apply_bass_correction,
    merge_consecutive,
)
from bass_detector import detect_bass_per_segment, pc_to_note


def fmt_time(t: float) -> str:
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:05.2f}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("audio", type=Path)
    p.add_argument("--out", type=Path, default=Path("eval_full_result.json"))
    p.add_argument("--min-dur", type=float, default=0.5)
    p.add_argument("--suspect-max-dur", type=float, default=3.0)
    p.add_argument("--bass-conf-ratio", type=float, default=2.5,
                   help="베이스 검출 신뢰도(top1/top2 비율). 낮으면 정정 건너뜀.")
    args = p.parse_args(argv)

    print(f"[1/5 키 감지] {args.audio}")
    t0 = time.time()
    key_root, key_mode = detect_key(args.audio)
    t_key = time.time() - t0
    print(f"  → {key_root} {key_mode}  ({t_key:.1f}s)")

    print(f"\n[2/5 chordino 추출] (demucs 분리 포함, 캐시됨)")
    t0 = time.time()
    raw = analyze_with_timing(args.audio, use_demucs_stem=True, use_harte_syntax=True)
    t_chordino = time.time() - t0
    print(f"  → {len(raw)} segments  ({t_chordino:.1f}s)")

    raw_merged = merge_consecutive(raw)
    print(f"  병합 후: {len(raw_merged)} segments")

    print(f"\n[3/5 짧은 잡음 필터 + 다이어토닉 보정]")
    t0 = time.time()
    s1 = filter_short_segments(raw, min_dur=args.min_dur)
    s1 = merge_consecutive(s1)
    s2 = apply_diatonic_correction(s1, key_root, key_mode, suspect_max_dur=args.suspect_max_dur)
    s2 = merge_consecutive(s2)
    t_pp = time.time() - t0
    print(f"  → {len(raw_merged)} → {len(s1)} → {len(s2)} segments  ({t_pp:.2f}s)")

    print(f"\n[4/5 베이스 검출] demucs bass stem (캐시 사용)")
    t0 = time.time()
    seg_with_bass = detect_bass_per_segment(args.audio, s2, confidence_ratio=args.bass_conf_ratio)
    t_bass = time.time() - t0
    detected = sum(1 for _, _, _, b, _ in seg_with_bass if b is not None)
    print(f"  → {detected}/{len(s2)} segments에서 베이스 신뢰도 충분  ({t_bass:.1f}s)")

    print(f"\n[5/5 베이스 보정]")
    s3 = apply_bass_correction(seg_with_bass, key_root, key_mode)
    s3 = merge_consecutive(s3)
    print(f"  → {len(s3)} segments")

    total = t_key + t_chordino + t_pp + t_bass
    print(f"\n[총 시간] {total:.1f}s  (key={t_key:.1f} + chordino={t_chordino:.1f} + 후처리={t_pp:.2f} + bass={t_bass:.1f})")

    # 출력
    print("\n" + "=" * 80)
    print("--- 단계별 진행 비교 ---")
    print("=" * 80)
    print(f"\n[원본 chordino]:")
    print(" - ".join(c for _, _, c in raw_merged))
    print(f"\n[+ 다이어토닉 보정]:")
    print(" - ".join(c for _, _, c in s2))
    print(f"\n[+ 베이스 보정]:")
    print(" - ".join(c for _, _, c in s3))

    print("\n" + "=" * 80)
    print("--- 최종 시간축 (with bass info) ---")
    print("=" * 80)
    for (start, end, _, bass_pc, conf), (_, _, final_chord) in zip(seg_with_bass, s3):
        bass_str = pc_to_note(bass_pc) if bass_pc is not None else "?"
        print(f"{fmt_time(start)} - {fmt_time(end)}  ({end-start:5.2f}s)  "
              f"bass={bass_str:<3} (conf={conf:4.1f})  → {final_chord}")

    payload = {
        "audio": str(args.audio),
        "key": f"{key_root} {key_mode}",
        "elapsed_total_sec": total,
        "elapsed": {
            "key_detection": t_key,
            "chordino": t_chordino,
            "postprocess": t_pp,
            "bass_detection": t_bass,
        },
        "raw_chordino": [{"start": s, "end": e, "chord": c} for s, e, c in raw_merged],
        "after_diatonic": [{"start": s, "end": e, "chord": c} for s, e, c in s2],
        "after_bass": [{"start": s, "end": e, "chord": c} for s, e, c in s3],
        "bass_info": [
            {"start": s, "end": e, "bass": pc_to_note(b) if b is not None else None,
             "confidence": conf}
            for s, e, _, b, conf in seg_with_bass
        ],
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[저장] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
