"""기능 4: 편곡된 코드 진행을 악보(PDF/PNG)로 생성

music21의 harmony.ChordSymbol로 코드 진행을 표기하고,
MuseScore가 설치되어 있으면 PDF/PNG로 렌더링한다.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

from music21 import chord as m21chord
from music21 import environment, harmony, metadata, meter, note, stream

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

MUSESCORE_CANDIDATES = [
    "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
    "/Applications/MuseScore 3.app/Contents/MacOS/mscore",
]


def _configure_musescore() -> Optional[str]:
    """music21이 MuseScore를 찾도록 환경 설정. 발견된 경로 반환."""
    env = environment.Environment()
    found = shutil.which("mscore") or shutil.which("musescore")
    if not found:
        for cand in MUSESCORE_CANDIDATES:
            if Path(cand).exists():
                found = cand
                break
    if found:
        env["musicxmlPath"] = found
        env["musescoreDirectPNGPath"] = found
    return found


def _build_score(chords: List[str], title: str = "Arranged Chord Progression") -> stream.Score:
    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = title

    part = stream.Part()
    part.append(meter.TimeSignature("4/4"))

    for symbol in chords:
        try:
            cs = harmony.ChordSymbol(symbol)
        except Exception:
            # 알 수 없는 토큰은 휴지부로 대체
            part.append(note.Rest(quarterLength=4.0))
            continue
        cs.quarterLength = 4.0  # 한 마디 = 한 코드
        # 화음 음표도 함께 추가해 시각적으로 코드 보이스를 표현
        pitches = [p.nameWithOctave for p in cs.pitches]
        if pitches:
            voiced = m21chord.Chord(pitches)
            voiced.quarterLength = 4.0
            part.append(cs)
            part.append(voiced)
        else:
            part.append(cs)

    score.append(part)
    return score


def generate_score(
    chords: List[str],
    output_basename: str = "arranged",
    formats: tuple[str, ...] = ("musicxml", "pdf"),
) -> List[Path]:
    """코드 진행을 악보 파일로 저장. 생성된 파일 경로 리스트를 반환."""
    if not chords:
        raise ValueError("코드 진행이 비어 있습니다.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    musescore_path = _configure_musescore()

    score = _build_score(chords)
    out_paths: List[Path] = []

    # MusicXML은 MuseScore가 없어도 항상 저장
    base = OUTPUT_DIR / output_basename
    xml_path = base.with_suffix(".musicxml")
    score.write("musicxml", fp=str(xml_path))
    out_paths.append(xml_path)

    if "pdf" in formats:
        if musescore_path is None:
            print(
                "[경고] MuseScore를 찾지 못해 PDF 출력을 건너뜁니다. "
                "MusicXML 파일은 정상 생성되었습니다."
            )
        else:
            try:
                pdf_path = Path(score.write("musicxml.pdf", fp=str(base.with_suffix(".pdf"))))
                out_paths.append(pdf_path)
            except Exception as e:
                print(f"[경고] PDF 변환 실패: {e}. PNG로 재시도합니다.")
                try:
                    png_path = Path(score.write("musicxml.png", fp=str(base.with_suffix(".png"))))
                    out_paths.append(png_path)
                except Exception as e2:
                    print(f"[경고] PNG 변환도 실패: {e2}")

    return out_paths
