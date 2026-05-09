"""Phase 0 spike: arrange_structured 동작 검증.

3가지 시나리오로 LLM 호출 → 결과 + 룰 베이스 검증 결과 출력.
실행: venv/bin/python scripts/test_arrange_structured.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# repo root을 import path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chord_postprocess import parse_key_string, validate_arrangement
from llm_arranger import (
    ArrangementInput,
    ArrangementOptions,
    arrange_structured,
)


SCENARIOS = [
    {
        "name": "A. C major / Jazz / 워킹 베이스",
        "input": ArrangementInput(
            current_chords=["C", "Am", "F", "G"],
            key="C major",
            options=ArrangementOptions(
                genre="Jazz",
                complexity="보통",
                tension="많음",
                bass_style="워킹 베이스",
                rhythm="싱코페이션",
            ),
        ),
    },
    {
        "name": "B. A minor / Lo-fi / 단순 / 루트 중심",
        "input": ArrangementInput(
            current_chords=["Am", "Dm", "E", "Am"],
            key="A minor",
            options=ArrangementOptions(
                genre="Lo-fi",
                complexity="단순",
                tension="적음",
                bass_style="루트 중심",
                rhythm="안정적",
            ),
        ),
    },
    {
        "name": "C. C major / City Pop / 복잡 / free_text",
        "input": ArrangementInput(
            current_chords=["C", "Am", "F", "G", "C", "Am", "F", "G"],
            key="C major",
            options=ArrangementOptions(
                genre="City Pop",
                complexity="복잡",
                tension="많음",
                bass_style="부드러운 연결",
                rhythm="싱코페이션",
            ),
            free_text="밤 드라이브, 잔잔하지만 세련된 느낌",
        ),
    },
]


def run_scenario(name: str, req: ArrangementInput) -> None:
    print(f"\n{'='*72}")
    print(f"  {name}")
    print(f"{'='*72}")
    print(f"입력 코드 : {' - '.join(req.current_chords)}")
    print(f"키        : {req.key}")
    opts = req.options
    print(f"옵션      : {opts.genre} / 복잡도={opts.complexity} / 텐션={opts.tension}")
    print(f"          : 베이스={opts.bass_style} / 리듬={opts.rhythm}")
    if req.free_text:
        print(f"자유 텍스트: {req.free_text}")

    try:
        out = arrange_structured(req)
    except Exception as e:
        print(f"\n[LLM 오류] {type(e).__name__}: {e}")
        return

    print(f"\n편곡 결과 : {' - '.join(out.chords)}")
    print(f"근거(LLM) : {out.rationale}")
    if out.warnings:
        print(f"경고(LLM) : {out.warnings}")

    # 룰 베이스 검증
    root, mode = parse_key_string(req.key)
    report = validate_arrangement(out.chords, root, mode)
    print(f"\n[룰 검증] foreign={report.foreign_count} / unparseable={report.unparseable_count}"
          f" / m21_fail={len(report.music21_failures)} / has_issues={report.has_issues}")
    for c in report.chords:
        marker = "OK " if c.issue is None else "!! "
        norm = f"→ {c.normalized}" if c.normalized != c.label else ""
        print(f"  {marker}{c.label:12} {norm:14} m21={c.music21_ok!s:5} {c.membership:12} {c.issue or ''}")


def main() -> int:
    for s in SCENARIOS:
        run_scenario(s["name"], s["input"])
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
