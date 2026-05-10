"""arrange_structured(Song 기반) 동작 검증 스파이크.

각 시나리오는 Song(파트 + 흐름)을 LLM에 보내고, 응답 구조가 입력과 일치하는지(파트 이름·
마디 수·각 마디 코드 수)와 함수 보존이 시각적으로 그럴듯한지 출력한다.

실행: venv/bin/python scripts/test_arrange_structured.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# repo root을 import path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_arranger import (
    ArrangementInput,
    Bar,
    Part,
    Song,
    arrange_structured,
)


SCENARIOS = [
    {
        "name": "A. G major / City Pop — 사랑하기 때문에 풍",
        "input": ArrangementInput(
            song=Song(
                parts=[
                    Part(
                        name="Verse",
                        bars=[
                            Bar(chords=["G", "CM7"]),
                            Bar(chords=["Bm7", "E7#5", "E7"]),
                            Bar(chords=["Am9", "C/D", "D7"]),
                            Bar(chords=["Gsus4", "G"]),
                        ],
                    ),
                ],
                structure=["Verse"],
            ),
            key="G major",
            bpm=82,
            genre="City Pop",
            free_text="밤 드라이브 느낌의 쓸쓸한 City Pop 발라드",
        ),
    },
    {
        "name": "B. C major / Jazz — ii-V-I 보존 테스트",
        "input": ArrangementInput(
            song=Song(
                parts=[
                    Part(
                        name="A",
                        bars=[
                            Bar(chords=["Dm7", "G7"]),
                            Bar(chords=["CM7"]),
                            Bar(chords=["Em7", "A7"]),
                            Bar(chords=["Dm7", "G7"]),
                        ],
                    ),
                ],
            ),
            key="C major",
            bpm=120,
            genre="Jazz",
        ),
    },
    {
        "name": "C. A minor / Ballad — 파트 2개 + structure 반복",
        "input": ArrangementInput(
            song=Song(
                parts=[
                    Part(
                        name="Verse",
                        bars=[
                            Bar(chords=["Am"]),
                            Bar(chords=["F", "G"]),
                            Bar(chords=["Em", "Am"]),
                            Bar(chords=["Dm", "E7"]),
                        ],
                    ),
                    Part(
                        name="Chorus",
                        bars=[
                            Bar(chords=["F", "G"]),
                            Bar(chords=["Em", "Am"]),
                            Bar(chords=["Dm", "G"]),
                            Bar(chords=["C", "E7"]),
                        ],
                    ),
                ],
                structure=["Verse", "Chorus", "Verse", "Chorus"],
            ),
            key="A minor",
            bpm=72,
            genre="Ballad",
            free_text="감성적이고 차분하게",
        ),
    },
]


def _shape_signature(parts):
    """파트별 (이름, 마디수, [마디별 코드 수]) 튜플 — 입력/출력 일치 검증용."""
    return [(p.name, len(p.bars), [len(b.chords) for b in p.bars]) for p in parts]


def run_scenario(name: str, req: ArrangementInput) -> None:
    print(f"\n{'=' * 72}")
    print(f"  {name}")
    print(f"{'=' * 72}")
    print(f"Key   : {req.key}")
    print(f"Genre : {req.genre}")
    if req.free_text:
        print(f"Free  : {req.free_text}")
    print()
    print("[입력]")
    for p in req.song.parts:
        bars_str = " | ".join(" ".join(b.chords) for b in p.bars)
        print(f"  {p.name}: {bars_str}")
    if req.song.structure:
        print(f"  Flow: {' → '.join(req.song.structure)}")

    try:
        out = arrange_structured(req)
    except Exception as e:
        print(f"\n[LLM 오류] {type(e).__name__}: {e}")
        return

    print()
    print("[편곡]")
    for p in out.parts:
        bars_str = " | ".join(" ".join(b.chords) for b in p.bars)
        print(f"  {p.name}: {bars_str}")

    print()
    print(f"근거: {out.rationale}")
    if out.warnings:
        print(f"경고: {out.warnings}")

    in_sig = _shape_signature(req.song.parts)
    out_sig = _shape_signature(out.parts)
    if in_sig == out_sig:
        print("\n[shape] OK — 파트/마디/코드 수 일치")
    else:
        print("\n[shape] MISMATCH")
        print(f"  입력 : {in_sig}")
        print(f"  출력 : {out_sig}")


def main() -> int:
    for s in SCENARIOS:
        run_scenario(s["name"], s["input"])
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
