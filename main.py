"""Music AI 메인 실행 파일

사용법:
    python main.py 음원파일.mp3
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from audio_analysis import analyze
from audio_renderer import render_audio
from llm_arranger import LLMArrangerError, confirm_and_arrange_interactive
from score_generator import generate_score


def _format_progression(chords: list[str]) -> str:
    return " - ".join(chords)


def run(audio_path: Path) -> int:
    print(f"[오디오 로드 + 코드 추출] {audio_path}")
    try:
        chords = analyze(audio_path)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"[오류] 오디오 분석 실패: {e}")
        return 1

    if not chords:
        print("[오류] 코드 진행을 추출하지 못했습니다.")
        return 1

    print(f"\n추출된 코드 진행: {_format_progression(chords)}")

    # LLM 편곡 (대화형)
    arranged: list[str] | None
    try:
        arranged = confirm_and_arrange_interactive(chords)
    except LLMArrangerError as e:
        print(f"[오류] {e}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\n사용자가 취소했습니다.")
        return 130

    target_chords = arranged if arranged else chords
    basename = "arranged" if arranged else "original"

    if arranged:
        print(f"\n편곡된 코드 진행: {_format_progression(arranged)}")
    else:
        print("\n편곡을 건너뛰고 추출된 코드 진행으로 결과물을 생성합니다.")

    # 악보 생성
    print("\n[악보 생성] music21 + MuseScore")
    try:
        score_paths = generate_score(target_chords, output_basename=basename)
        for p in score_paths:
            print(f"  → {p}")
    except Exception as e:
        print(f"[경고] 악보 생성 중 오류: {e}")
        traceback.print_exc()

    # 오디오 렌더링
    print("\n[오디오 생성] pretty_midi + fluidsynth")
    try:
        wav_path = render_audio(target_chords, output_basename=basename)
        print(f"  → {wav_path}")
    except Exception as e:
        print(f"[오류] 오디오 렌더링 실패: {e}")
        traceback.print_exc()
        return 1

    print("\n완료. 결과물은 output/ 폴더에 있습니다.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="음원 파일을 분석해 코드 진행을 추출하고, LLM으로 편곡한 뒤 악보/오디오를 생성합니다."
    )
    parser.add_argument("audio", type=Path, help="입력 음원 파일 경로")
    args = parser.parse_args(argv)
    return run(args.audio)


if __name__ == "__main__":
    sys.exit(main())
